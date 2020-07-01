FROM python:3.7.8-slim-stretch@sha256:2dae8c3a67400c05270bc7f6c7bba46b0fc13a702d4a3ab9856f7e3840908154 as socorro_image_base

# Set up user and group
ARG groupid=10001
ARG userid=10001

WORKDIR /app/
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app && \
    chown app:app /app/

# Install OS-level things
COPY ./docker/set_up_ubuntu.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh


FROM socorro_image_base as socorro_breakpad
WORKDIR /mdsw/

# Install breakpad requirements and some helpful debugging things
RUN apt-get update && apt-get install -y \
    gdb \
    libcurl3 \
    libcurl3-gnutls \
    libcurl4-gnutls-dev \
    pkg-config \
    rsync \
    vim \
    wget \
&& rm -rf /var/lib/apt/lists/*

# Build breakpad client and stackwalker binaries
COPY ./scripts/build-breakpad.sh /mdsw/scripts/
COPY ./scripts/build-stackwalker.sh /mdsw/scripts/
COPY ./minidump-stackwalk/ /mdsw/minidump-stackwalk/
RUN STACKWALKDIR=/stackwalk SRCDIR=/mdsw /mdsw/scripts/build-stackwalker.sh

# Let app own /mdsw and /stackwalk so it's easier to debug later
RUN chown -R app:app /mdsw /stackwalk


FROM socorro_image_base
WORKDIR /app/

# Copy stackwalk bits
COPY --from=socorro_breakpad /stackwalk/* /stackwalk/

# Install frontend JS deps
COPY ./webapp-django/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

# Install Socorro Python requirements
COPY --chown=app:app ./requirements /app/requirements
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements/default.txt -c requirements/constraints.txt && \
    pip check --disable-pip-version-check

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LESS_BINARY=/webapp-frontend-deps/node_modules/.bin/lessc \
    UGLIFYJS_BINARY=/webapp-frontend-deps/node_modules/.bin/uglifyjs \
    CSSMIN_BINARY=/webapp-frontend-deps/node_modules/.bin/cssmin \
    NPM_ROOT_PATH=/webapp-frontend-deps/ \
    NODE_PATH=/webapp-frontend-deps/node_modules/

# app should own everything under /app in the container
USER app

# Copy everything over
COPY --chown=app:app . /app/

# Build tmp directories for minidump stackwalker
RUN mkdir -p /tmp/symbols/cache /tmp/symbols/tmp

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp-django/ && python manage.py collectstatic --noinput

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/docker/socorro_entrypoint.sh"]
