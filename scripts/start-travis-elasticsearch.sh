#!/bin/bash

set -ex

# Why download it and not use the elasticsearch service?
# Two reasons
#  - predictable version (1.4.x) is what we use in production
#  - running it as a service would require sudo which we don't want to use
wget --no-check-certificate 'https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-1.4.5.tar.gz'
tar zxf elasticsearch-1.4.5.tar.gz
echo "script.disable_dynamic: false" > elasticsearch.yml
# the -d flag starts it as a daemon in the background
./elasticsearch-1.4.5/bin/elasticsearch -d --config=elasticsearch.yml
