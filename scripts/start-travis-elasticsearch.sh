#!/bin/bash

set -ex

# Why download it and not use the elasticsearch service?
# Two reasons
#  - predictable version (5.1.x) is what we use in production
#  - running it as a service would require sudo which we don't want to use
wget --no-check-certificate 'https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-5.1.1.tar.gz'
tar zxf elasticsearch-5.1.1.tar.gz
echo "script.disable_dynamic: false" > elasticsearch.yml
echo "index.number_of_shards: 1" >> elasticsearch.yml
echo "index.number_of_replicas: 0" >> elasticsearch.yml
# the -d flag starts it as a daemon in the background
./elasticsearch-5.1.1/bin/elasticsearch -d --config=elasticsearch.yml
