#!/bin/bash
#
# Quick bootstrap script for an Ubuntu Lucid host
#
# This allows you to bootstrap any Lucid box (VM, physical hardware, etc)
# using Puppet and automatically install a full Socorro environment on it.
#

apt-get install git-core puppet rsync

GIT_REPO_URL="git://github.com/mozilla/socorro.git"

mkdir /puppet

# Clone the project from github
useradd socorro
groupadd admin
su - socorro
mkdir dev
cd dev
git clone $GIT_REPO_URL socorro

# copy the files from the git checkout to /puppet
rsync -a /home/socorro/dev/socorro/puppet/ /puppet/
exit

# Let puppet take it from here...
puppet /home/socorro/dev/puppet/manifests/*.pp

