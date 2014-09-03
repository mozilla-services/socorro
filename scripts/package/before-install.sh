#! /bin/bash -e

# Create a new socorro user
useradd socorro 2> /dev/null

chmod o+x /home/socorro

mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent

chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback

chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback

for service in socorro-processor; do
  if [ -f /etc/init.d/${service} ]; then
    service ${service} stop
  fi
done
