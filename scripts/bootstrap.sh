#! /bin/bash -ex

export VIRTUAL_ENV=${VIRTUAL_ENV:-"$PWD/socorro-virtualenv"}

git submodule update --init --recursive

if [[ ! "$(type -p lessc)" ]]; then
    printf "\e[0;32mlessc not found! less must be installed and lessc on your path to build socorro.\e[0m\n" && exit 1
fi

if [ ! -d "$VIRTUAL_ENV" ]; then
    virtualenv -p python2.6 ${VIRTUAL_ENV}
fi
source "$VIRTUAL_ENV/bin/activate"

# install dev + prod dependencies
${VIRTUAL_ENV}/bin/pip install tools/peep-1.2.tar.gz
${VIRTUAL_ENV}/bin/peep install --download-cache=./pip-cache -r requirements.txt

# pull pre-built, known version of breakpad
wget --quiet 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
tar -zxf breakpad.tar.gz
mv breakpad stackwalk
# Build JSON stackwalker
pushd minidump-stackwalk
make
popd
cp minidump-stackwalk/stackwalker stackwalk/bin

# bootstrap webapp
pushd webapp-django
./bin/bootstrap.sh
popd
