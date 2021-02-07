import boto3
import io
import os
import time
import paramiko
from script_commands_list import common_commands


def log(msg):
    print("\n\n####\n", msg, "\n####\n\n")


def _instances_in_pending_state(instance_ids):
    for instance_id in instance_ids:
        if ec2_resource.Instance(instance_id).state.get('Name') == 'pending':
            return True
    return False


KEY_NAME = 'test_key_1'
SECURITY_GROUP_NAME = 'TestSG1'

ec2_resource = boto3.resource('ec2')
ec2_client = boto3.client("ec2")


# create key pair
key_pair = ec2_resource.create_key_pair(
    KeyName=KEY_NAME
)
key_value = key_pair.key_material
print(key_value)

with io.open(f"{KEY_NAME}.pem", "w", encoding="utf-8") as f1:
    f1.write(str(key_value))
    f1.close()

os.chmod(f"{KEY_NAME}.pem", 0o400)

log("Creating Security Group")
sg = ec2_client.create_security_group(
    Description='SSH_ACCESS',
    GroupName=SECURITY_GROUP_NAME
)

log(sg)
sg_group_id = sg.get('GroupId')

log(sg_group_id)
log("Creating inbound rule")
ec2_client.authorize_security_group_ingress(
    GroupId=sg_group_id,
    IpPermissions=[
        {
            'FromPort': 0,
            'IpProtocol': '-1',
            'IpRanges': [
                {
                    'CidrIp': '0.0.0.0/0',

                },
            ],
            'ToPort': 65536,
        }
    ]
)

log("Creating instance")
instances = ec2_resource.create_instances(
    ImageId='ami-0a4a70bd98c6d6441',
    InstanceType='t2.micro',
    KeyName=KEY_NAME,
    MinCount=3,
    MaxCount=3,
    SecurityGroupIds=[
        sg_group_id
    ],
    BlockDeviceMappings=[
        {
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': 10,
                'VolumeType': 'gp2',
                'Encrypted': True
            }
        }
    ]
)

log(instances)

instance_ids = [instance.id for instance in instances]
log(instance_ids)

while _instances_in_pending_state(instance_ids):
    print("Instances still in pending state...")
    time.sleep(5)

replica_set_members = [
    ec2_resource.Instance(instance_ids[0]),
    ec2_resource.Instance(instance_ids[1]),
    ec2_resource.Instance(instance_ids[2])
]


print("Executing SSH commands in 60 seconds...")
time.sleep(60)

key = paramiko.RSAKey.from_private_key_file(f"{KEY_NAME}.pem")
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

time.sleep(5)

for i in range(0, 2):
    ssh_client.connect(
        hostname=replica_set_members[i].public_ip_address,
        username="ubuntu",
        pkey=key
    )

    commands = [
        "sudo bash -c 'echo %s > /etc/hostname && hostname -F /etc/hostname'" % (
            replica_set_members[i].public_dns_name)
    ]
    for command in common_commands:
        commands.append(command)
    for command in commands:
        print("\n\n#####\n")
        print(f"Executing {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print("OUTPUT: ", str(stdout.read()))
        print("ERROR: ", str(stderr.read()))
        print("\n#####\n\n")


# 3rd member
ssh_client.connect(
    hostname=replica_set_members[2].public_ip_address,
    username="ubuntu",
    pkey=key
)

replica_set_initiate_command = '''
    rs.initiate(
        {
            _id: \"test-replica-set\",
            members: [
                { _id: 0, host: \"%s\" },
                { _id: 1, host: \"%s\" },
                { _id: 2, host: \"%s\" }
            ]
        }
    )
    rs.status()
''' % (
    replica_set_members[0].public_dns_name,
    replica_set_members[1].public_dns_name,
    replica_set_members[2].public_dns_name
)

replica_creation_commands = [
    '''
    echo '
    %s
    ' > mdb_script.js
    ''' % (replica_set_initiate_command),
    "sleep 10",
    "mongo < mdb_script.js"]

commands = [
    "sudo bash -c 'echo %s > /etc/hostname && hostname -F /etc/hostname'" % (
        replica_set_members[2].public_dns_name)
]

for command in common_commands:
    commands.append(command)

for command in replica_creation_commands:
    commands.append(command)

for command in commands:
    print("\n\n#####\n")
    print(f"Executing {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print("OUTPUT: ", str(stdout.read()))
    print("ERROR: ", str(stderr.read()))
    print("\n#####\n\n")

log("3 Node replica set created!")
