#! /bin/bash -e

# run socorro integration test
echo "Running integration test..."
./scripts/rabbitmq-integration-test.sh --destroy
./scripts/rabbitmq-integration-test-2015.sh --destroy
