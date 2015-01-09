#! /bin/bash -xe

source scripts/defaults
source "$VIRTUAL_ENV/bin/activate"

pushd docs
make html
popd
