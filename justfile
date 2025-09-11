# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

_default:
    @just --list

_env:
    #!/usr/bin/env sh
    if [ ! -f .env ]; then
      echo "Copying docker/config/.env.dist to .env..."
      cp docker/config/.env.dist .env
    fi

# Build docker images
build *args='app fakesentry oidcprovider elasticsearch postgresql pubsub memcached gcs-emulator': _env
    # Create these two directories using the current user so they don't end up
    # created by Docker with the wrong ownership; ignore errors
    -mkdir webapp/static/ webapp/node_modules/
    docker compose build --progress plain {{args}}

# Set up Postgres, Elasticsearch, local Pub/Sub, and local GCS services.
setup: _env
    docker compose run --rm app shell /app/bin/setup_services.sh
    bin/create_superuser.sh

# Add/update necessary database data.
update-data: _env
    docker compose run --rm app shell /app/bin/update_data.sh

# Run services, defaults to socorro and fakesentry for debugging
run *args='--attach=processor --attach=webapp --attach=fakesentry processor webapp': _env
    docker compose up {{args}}

# Run stage submitter and fake collector
run-submitter *args='--attach=stage_submitter --attach=fakecollector': _env
    docker compose up \
        {{args}} \
        stage_submitter \
        fakecollector

# Stop service containers.
stop *args:
    docker compose stop {{args}}

# Remove service containers and networks.
down *args:
    docker compose down {{args}}

# Open a shell or run a command in the app container.
shell *args='/bin/bash': _env
    docker compose run --rm --entrypoint= app {{args}}

# Open a shell or run a command in the test environment.
test-shell *args='/bin/bash':
    docker compose run --rm --entrypoint= test {{args}}

# Remove all build, test, coverage, and Python artifacts.
clean:
    -rm -rf .cache
    @echo "Skipping deletion of symbols/ in case you have data in there."

# Generate Sphinx HTML documentation.
docs: _env
    docker compose run --rm app shell make -C docs/ clean
    docker compose run --rm app shell make -C docs/ html

# Lint code, or use --fix to reformat and apply auto-fixes for lint.
lint *args: _env
    docker compose run --rm --no-deps app shell ./bin/lint.sh {{args}}

# Open psql cli.
psql *args:
    docker compose run --rm postgresql psql postgresql://postgres:postgres@postgresql/socorro {{args}}

# Run tests.
test *args:
    docker compose run --rm test shell ./bin/test.sh {{args}}

# Build requirements.txt file after requirements.in changes.
rebuild-reqs *args: _env
    docker compose run --rm --no-deps app shell pip-compile --generate-hashes --strip-extras {{args}}

# Verify that the requirements file is built by the version of Python that runs in the container.
verify-reqs: _env
    docker compose run --rm --no-deps app shell ./bin/verify_reqs.sh

# Check how far behind different server environments are from main tip.
service-status *args: _env
    docker compose run --rm --no-deps app shell service-status {{args}}
