#! /bin/bash -ex

echo "this is test-puppet.sh"

# lint puppet manifests; bug 976639
pushd puppet
find . -name '*.pp' -exec puppet parser validate {} \; -exec puppet-lint $puppet_lint_args {} \;
popd
