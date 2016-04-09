#! /bin/bash -ex

echo "this is bootstrap.sh"

source scripts/defaults

git submodule update --init --recursive

if [ ! -d "$VIRTUAL_ENV" ]; then
    virtualenv -p $PYTHON ${VIRTUAL_ENV}
fi
source "$VIRTUAL_ENV/bin/activate"

# install dev + prod dependencies
${VIRTUAL_ENV}/bin/python tools/pipstrap.py

${VIRTUAL_ENV}/bin/pip install --require-hashes -r requirements.txt

if [ -n "${SOCORRO_DEVELOPMENT_ENV+1}" ]; then
    # install development egg in local virtualenv
    ${VIRTUAL_ENV}/bin/python setup.py develop
fi

if [ "`uname -sm`" == "Linux x86_64" ]; then
  # pull pre-built, known version of breakpad
  wget -N --quiet 'https://queue.taskcluster.net/v1/task/OBPgU_HqTiuS2EwwIvosUQ/runs/0/artifacts/public%2Fbreakpad.tar.gz'
  tar -zxf breakpad.tar.gz
  rm -rf stackwalk
  mv breakpad stackwalk
else
  # build breakpad from source
  make breakpad
fi
# Build JSON stackwalker and friends
pushd minidump-stackwalk
make
popd
cp minidump-stackwalk/stackwalker stackwalk/bin
cp minidump-stackwalk/jit-crash-categorize stackwalk/bin
cp minidump-stackwalk/dumplookup stackwalk/bin

# setup any unset test configs and databases without overwriting existing files
pushd config
for file in *.ini-dist; do
    if [ ! -f `basename $file -dist` ]; then
        cp $file `basename $file -dist`
    fi
done
popd

# bootstrap webapp
OLD_PYTHONPATH=$PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
pushd webapp-django
./bin/bootstrap.sh
export PYTHONPATH=$OLD_PYTHONPATH

popd
