#! /bin/bash

/sbin/service socorro-processor stop

chkconfig --del socorro-processor

userdel socorro
