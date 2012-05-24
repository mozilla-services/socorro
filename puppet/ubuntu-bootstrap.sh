#!/bin/bash
#
# Quick bootstrap script for an Ubuntu Lucid host
#
# This allows you to bootstrap any Lucid box (VM, physical hardware, etc)
# using Puppet and automatically install a full Socorro environment on it.
#
# NOTE - if you want HBase installed (which you need for processing incoming
#        crashes, uncomment socorro-hbase.pp in puppet/manifests/nodes/nodes.pp

apt-get update && apt-get install git-core puppet

GIT_REPO_URL="git://github.com/mozilla/socorro.git"

mkdir /puppet

# Clone the project from github
useradd -m socorro
groupadd admin
su - socorro -c "mkdir -p dev && cd dev && git clone $GIT_REPO_URL socorro"

# Let puppet take it from here...
puppet /home/socorro/dev/socorro/puppet/manifests/init.pp

