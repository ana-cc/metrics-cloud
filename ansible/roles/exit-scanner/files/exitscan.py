
import collections
import datetime
import glob
import json
import os
import os.path
import re
import subprocess

import stem.descriptor

fortyeighthoursago = datetime.datetime.utcnow() - datetime.timedelta(hours=48)

Measurement = collections.namedtuple("Measurement", ["address", "date"])
exits = dict()


def merge_addresses(fp, new):
    addresses = exits[fp].exit_addresses
    addresses.extend(new)
    addresses.sort(key=lambda x: x[1], reverse=True)
    uniq_addresses = []
    while len(uniq_addresses) < len(addresses):
        if addresses[len(uniq_addresses)][0] in uniq_addresses:
            addresses.remove(addresses[len(uniq_addresses)])
            continue
        uniq_addresses.append(addresses[len(uniq_addresses)][0])
    return [
        a for a in addresses
        if a[1] > fortyeighthoursago
    ]


def merge(desc):
    if desc.fingerprint not in exits:
        exits[desc.fingerprint] = desc
        return
    fp = desc.fingerprint
    exits[fp].published = max(exits[fp].published, desc.published)
    exits[fp].last_status = max(exits[fp].last_status, desc.last_status)
    exits[fp].exit_addresses = merge_addresses(fp, desc.exit_addresses)


def run():
    exit_lists = list(glob.iglob('lists/2*')) # fix this glob before 23:59 on 31st Dec 2999

    # Import latest exit list from disc
    if exit_lists:
        latest_exit_list = max(exit_lists, key=os.path.getctime)
        for desc in stem.descriptor.parse_file(latest_exit_list,
                                               descriptor_type="tordnsel 1.0"):
            merge(desc)

    # Import new measurements
    with subprocess.Popen(["./bin/exitmap", "ipscan", "-o", "/dev/stdout"],
                          cwd="/srv/exitscanner.torproject.org/exitscanner/exitmap",
                          stdout=subprocess.PIPE,
                          encoding='utf-8') as p:
        for line in p.stdout:
            print(line)
            result = re.match(
                r"^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}),[0-9]{3} modules\.ipscan \[INFO\] (\{.*\})$",
                line)
            if result:
                print(result)
                check_result = json.loads(result.group(2))
                desc = stem.descriptor.tordnsel.TorDNSEL("", False)
                desc.fingerprint = check_result["Fingerprint"]
                desc.last_status = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                desc.published = datetime.datetime.strptime(
                    check_result["DescPublished"], "%Y-%m-%dT%H:%M:%S")
                desc.exit_addresses = [
                    (check_result["IP"],
                     datetime.datetime.strptime(result.group(1),
                                                "%Y-%m-%d %H:%M:%S"))
                ]
                merge(desc)

    # Format exit list filename
    now = datetime.datetime.utcnow()
    filename = (f"{now.year}-{now.month:02d}-"
                f"{now.day:02d}-{now.hour:02d}-"
                f"{now.minute:02d}-{now.second:02d}")

    # Format an exit list
    with open(f"lists/{filename}", "w") as out:
        for desc in exits.values():
            if desc.exit_addresses:
                out.write(f"ExitNode {desc.fingerprint}\n")
                out.write(f"Published {desc.published}\n")
                out.write(f"LastStatus {desc.last_status}\n")
                for a in desc.exit_addresses:
                    out.write(f"ExitAddress {a[0]} {a[1]}\n")

    # Provide the snapshot emulation
    os.unlink("lists/latest")
    os.symlink(os.path.abspath(f"lists/{filename}"), "lists/latest")

if __name__ == "__main__":
    while True:
        start = datetime.datetime.utcnow()
        run()
        while datetime.datetime.utcnow() < start + datetime.timedelta(minutes=40):
            pass
