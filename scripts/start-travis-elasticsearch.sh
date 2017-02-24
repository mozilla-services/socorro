#!/bin/bash

set -ex

# Why download it and not use the elasticsearch service?
# Two reasons
#  - predictable version (5.1.x) is what we use in production
#  - running it as a service would require sudo which we don't want to use
wget --no-check-certificate 'https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.1.1.tar.gz'
tar zxf elasticsearch-5.1.1.tar.gz

# Increase the limit of mmap counts in virtual memory. See:
# https://www.elastic.co/guide/en/elasticsearch/reference/5.1/vm-max-map-count.html
sysctl -w vm.max_map_count=262144

# the -d flag starts it as a daemon in the background
./elasticsearch-5.1.1/bin/elasticsearch -d
