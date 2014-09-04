#! /bin/bash -e

source scripts/defaults

# make the analysis
git submodule update --init socorro-toolbox akela
cd akela && mvn package; cd ../
cd socorro-toolbox && mvn package; cd ../
mkdir -p analysis
rsync socorro-toolbox/target/*.jar analysis/
rsync akela/target/*.jar analysis/
rsync -a socorro-toolbox/src/main/pig/ analysis/
