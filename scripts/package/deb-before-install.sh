#! /bin/bash -e

# Create a new socorro user
set +e
grep socorro /etc/passwd 2>&1 > /dev/null
if [ $? -ne 0 ]; then
    useradd -m socorro 2> /dev/null
fi
set -e

chmod o+x /home/socorro

mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent

chown www-data:socorro /home/socorro/primaryCrashStore /home/socorro/fallback

chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback

for service in socorro-processor; do
  if [ -f /etc/init.d/${service} ]; then
    service ${service} stop
  fi
done
