#! /bin/bash -ex

source scripts/defaults

git submodule update --init --recursive

if [[ ! "$(type -p lessc)" ]]; then
    printf "\e[0;32mlessc not found! less must be installed and lessc on your path to build socorro.\e[0m\n" && exit 1
fi

if [ ! -d "$VIRTUAL_ENV" ]; then
    virtualenv -p python2.6 ${VIRTUAL_ENV}
fi
source "$VIRTUAL_ENV/bin/activate"

# install dev + prod dependencies
${VIRTUAL_ENV}/bin/pip install tools/peep-2.0.tar.gz
${VIRTUAL_ENV}/bin/peep install --download-cache=./pip-cache -r requirements.txt

if [ "`uname -sm`" == "Linux x86_64" ]; then
  # pull pre-built, known version of breakpad
  wget -N --quiet 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
  tar -zxf breakpad.tar.gz
  rm -rf stackwalk
  mv breakpad stackwalk
else
  # build breakpad from source
  make breakpad
fi
# Build JSON stackwalker
pushd minidump-stackwalk
make
popd
cp minidump-stackwalk/stackwalker stackwalk/bin

# bootstrap webapp
pushd webapp-django
./bin/bootstrap.sh
popd
