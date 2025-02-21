# This should be kept in sync with the python version used in docker/Dockerfile
FROM --platform=linux/amd64 mcr.microsoft.com/devcontainers/python:3.11-bookworm@sha256:138c451b17c1c5930f77e71a6510a0bae1d7b77feff5e0a714a22fa3d757a51f AS devcontainer_amd64

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

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --no-deps -r requirements.txt && \
    pip install --no-cache-dir ipython && \
    pip check --disable-pip-version-check

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UGLIFYJS_BINARY=/app/webapp/node_modules/.bin/uglifyjs \
    NPM_ROOT_PATH=/app/webapp/ \
    NODE_PATH=/app/webapp/node_modules/

# Install frontend JS deps
COPY --chown=app:app ./webapp/package*.json /app/webapp/
RUN cd /app/webapp/ && npm ci

