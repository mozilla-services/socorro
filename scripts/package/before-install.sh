#! /bin/bash -e

# Create a new socorro user if they don't already exist
id socorro || useradd socorro

# ensure base directories exist
mkdir -p /etc/socorro
mkdir -p /var/log/socorro
chown socorro /var/log/socorro
mkdir -p /data/socorro
mkdir -p /var/lock/socorro
chown socorro /var/lock/socorro
mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent
chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback
chmod o+x /home/socorro
chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback
