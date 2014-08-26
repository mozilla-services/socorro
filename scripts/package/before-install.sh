#! /bin/bash -e

# Create a new socorro user if they don't already exist
id socorro || useradd socorro

chmod o+x /home/socorro

mkdir -p /home/socorro/primaryCrashStore \
    /home/socorro/fallback \
    /home/socorro/persistent

chown apache:socorro /home/socorro/primaryCrashStore /home/socorro/fallback

chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback
