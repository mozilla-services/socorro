#! /bin/bash
INSTALL_PREFIX=/data

service socorro-processor stop

userdel -r socorro 2>&1 > /dev/null
