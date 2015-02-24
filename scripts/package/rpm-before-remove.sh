#! /bin/bash

service socorro-processor stop

chkconfig --del socorro-processor

userdel socorro
