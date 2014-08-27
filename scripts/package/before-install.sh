#! /bin/bash -e

# Create a new socorro user if they don't already exist
id socorro || useradd socorro

chmod o+x /home/socorro

mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent

chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback

chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback

for service in socorro-processor httpd
do
  if [ -f /etc/init.d/${service} ]
  then
    /sbin/service ${service} stop
  fi
done
