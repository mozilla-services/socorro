#!/bin/bash

set -ex

# Why download it and not use the elasticsearch service?
# Two reasons
#  - predictable version (5.3.x) is what we use in production
#  - running it as a service would require sudo which we don't want to use
wget --no-check-certificate 'https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.3.3.deb'
sudo dpkg -i --force-confnew elasticsearch-5.3.3.deb

sudo service elasticsearch start
