#! /bin/bash

function error {
  if [ $# != 2 ]
  then
    echo "Syntax: error <exit_code> <message>"
    exit 1
  fi
  EXIT_CODE=$1
  MESSAGE=$2
  if [ $EXIT_CODE != 0 ]
  then
    echo "ERROR: $MESSAGE"
    exit $EXIT_CODE
  fi
}

# ensure socorro user exists
id socorro &> /dev/null
if [ $? != 0 ]; then
    echo "Creating socorro user"
    useradd socorro
    error $? "could not create socorro user"
fi

# ensure base directories exist
echo "Creating system config, log and crash storage directories"
mkdir -p /etc/socorro
error $? "could not create /etc/socorro"
mkdir -p /var/log/socorro
error $? "could not create /var/log/socorro"
chown socorro /var/log/socorro
error $? "could not chown /var/log/socorro"
mkdir -p /data/socorro
error $? "could not create /data/socorro"
mkdir -p /var/lock/socorro
error $? "could not create /var/lock/socorro"
chown socorro /var/lock/socorro
error $? "could not chown /var/lock/socorro"
mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent
error $? "could not make socorro crash storage directories"
chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback
error $? "could not chown apache on crash storage directories, is httpd installed?"
chmod o+x /home/socorro
error $? "could not chmod o+x socorro homedir"
chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback
error $? "could not chmod crash storage directories"
