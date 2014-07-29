#! /bin/bash

git submodule update --init --recursive

if [[ ! "$(type -p lessc)" ]]; then
    printf "\e[0;32mlessc not found! less must be installed and lessc on your path to build socorro.\e[0m\n" && exit 1
fi

if [ ! -d "$VIRTUAL_ENV" ]; then
    virtualenv -p python2.6 ${PWD}/socorro-virtualenv
    source ${PWD}/socorro-virtualenv/bin/activate
    export VIRTUAL_ENV
fi

# install dev + prod dependencies
${VIRTUAL_ENV}/bin/pip install tools/peep-1.2.tar.gz
${VIRTUAL_ENV}/bin/peep install --download-cache=./pip-cache -r requirements.txt

# bootstrap webapp
cd webapp-django; ./bin/bootstrap.sh
