# This should be kept in sync with the python version used in docker/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye@sha256:105bf6a63ab025206f019a371a735fec6553db0be520030c7a2fd0e002947232

ARG userid=10001
ARG groupid=10001

WORKDIR /app

# add a non-privileged user for installing and running the application
# We use --non-unique in case $groupid/$userid collide with the existing "vscode" user.
# useradd -g app --uid $userid --non-unique --shell /usr/sbin/nologin --create-home app && \
RUN groupadd --gid $groupid --non-unique app && \
    useradd -g app --uid $userid --non-unique --shell /bin/bash --create-home app && \
    chown app:app /app/

# Install Debian packages
RUN apt-get update && \
    apt-get install -y ripgrep tig

# Install OS-level things
COPY docker/set_up_ubuntu.sh /tmp/set_up_ubuntu.sh
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh && \
    rm /tmp/set_up_ubuntu.sh

# Install stackwalker
COPY docker/set_up_stackwalker.sh /tmp/set_up_stackwalker.sh
RUN /tmp/set_up_stackwalker.sh && \
    rm /tmp/set_up_stackwalker.sh

# Install frontend JS deps
COPY --chown=app:app ./webapp/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir --no-deps -r requirements.txt && \
    pip install --no-cache-dir ipython && \
    pip check --disable-pip-version-check

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LESS_BINARY=/webapp-frontend-deps/node_modules/.bin/lessc \
    UGLIFYJS_BINARY=/webapp-frontend-deps/node_modules/.bin/uglifyjs \
    CSSMIN_BINARY=/webapp-frontend-deps/node_modules/.bin/cssmin \
    NPM_ROOT_PATH=/webapp-frontend-deps/ \
    NODE_PATH=/webapp-frontend-deps/node_modules/
