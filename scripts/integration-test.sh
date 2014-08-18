#! /bin/bash -e

# pull pre-built, known version of breakpad
wget --quiet 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
tar -zxf breakpad.tar.gz
mv breakpad stackwalk
make stackwalker

# run socorro integration test
echo "Running integration test..."
./scripts/rabbitmq-integration-test.sh --destroy
./scripts/elasticsearch-integration-test.sh
