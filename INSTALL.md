Clone socorro-crashstats, and check out crashstats-init branch
=======
git clone https://github.com/rhelmer/socorro-crashstats
cd socorro-crashstats
git checkout crashstats-init

Clone vendor repositories
=======
git submodule update --init --recursive

Create virtualenv and populate it
=======
virtualenv .virtualenv
source .virtualenv/bin/activate
pip install -r requirements/prod.txt
pip install -r requirements/dev.txt

Copy default config file and customize it
=======
cp crashstats/settings/local.py-dist crashstats/settings/local.py

Run the dev server, by default will listen on http://localhost:8000
=======
./manage.py runserver
