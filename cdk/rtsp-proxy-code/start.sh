
#get the output of ec2 metadata security-credentials
#this gives the name of the role that is attached to the instance
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/ > role_name.txt
# now to get role specific credentials append the role name to the url and curl again
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/$(cat role_name.txt) > credentials.json
#Sample output of credentials.json

#Sample output: ip-10-0-41-219.ap-southeast-2.compute.internal
# we need to extract the region name from the hostname
curl http://169.254.169.254/latest/meta-data/hostname > hostname.txt
#Sample output: ip-10-0-41-219.ap-southeast-2.compute.internal
#split the output by '.' and get the second element
region=$(cat hostname.txt | cut -d '.' -f 2)

#export it into environment variables
#      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
#      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
#      - AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
export AWS_ACCESS_KEY_ID=$(cat credentials.json | jq -r '.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(cat credentials.json | jq -r '.SecretAccessKey')
export AWS_SESSION_TOKEN=$(cat credentials.json | jq -r '.Token')
export AWS_DEFAULT_REGION=$region

