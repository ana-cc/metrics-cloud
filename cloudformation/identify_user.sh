#!/bin/zsh
#aws ec2 describe-key-pairs | jq -r '.KeyPairs[].KeyName' | grep `aws iam get-user | jq -r .User.UserName`
declare -A keypairs
keypairs[acute]="acute yubikey 4"
keypairs[irl]="irl macbook 16"
keypairs[karsten]="karsten's key"

cur_user=$(aws iam get-user | jq -r .User.UserName)

for key val in ${(kv)keypairs}; do
    if [ $key = $cur_user ]; then
        echo $val;
        break
    fi
done

