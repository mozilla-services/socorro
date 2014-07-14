#! /bin/bash

VIRTUALENV=$PWD/socorro-virtualenv

git submodule update --init --recursive

if [[ ! "$(type -p lessc)" ]]; then
    printf "\e[0;32mlessc not found! less must be installed and lessc on your path to build socorro.\e[0m\n" && exit 1
fi

[ -d $VIRTUALENV ] || virtualenv -p python2.6 $VIRTUALENV

# install dev + prod dependencies
$VIRTUALENV/bin/pip install tools/peep-1.2.tar.gz
$VIRTUALENV/bin/peep install --download-cache=./pip-cache -r requirements.txt

# bootstrap webapp
cd webapp-django; ./bin/bootstrap.sh
