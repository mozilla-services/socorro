#! /bin/bash

# ensure base directories owned
chown socorro /var/log/socorro
chown socorro /var/lock/socorro

# FIXME processor will silently fail if this does not exist :/
mkdir /home/socorro/temp
chown socorro /home/socorro/temp

# Link the local Django settings to the distributed settings.
ln -fs /etc/socorro/local.py \
    /data/socorro/webapp-django/crashstats/settings/local.py

# make sure systemd reads the latest service files
systemctl daemon-reload

# we've dropped in nginx config files, reload them
systemctl reload nginx
