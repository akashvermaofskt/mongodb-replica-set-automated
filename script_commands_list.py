common_commands = [
    'wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -',
    'echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list',
    'sudo apt-get update',
    'sudo apt-get install -y mongodb-org',
    'sudo systemctl start mongod',
    '''
        echo "
# mongod.conf

# for documentation of all options, see:
#   http://docs.mongodb.org/manual/reference/configuration-options/

# Where and how to store data.
storage:
  dbPath: /var/lib/mongodb
  journal:
    enabled: true

#  engine:
#  mmapv1:
#  wiredTiger:

# where to write logging data.
systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

# network interfaces
net:
  port: 27017
  bindIpAll: true

# how the process runs
processManagement:
  timeZoneInfo: /usr/share/zoneinfo

#security:

#operationProfiling:

replication:
  replSetName: \"test-replica-set\"

#sharding:

## Enterprise-Only Options:

#auditLog:

#snmp:
" | sudo tee /etc/mongod.conf
        ''',
    'sudo service mongod restart']
