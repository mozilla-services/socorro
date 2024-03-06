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

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir --no-deps -r requirements.txt && \
    pip install --no-cache-dir ipython && \
    pip check --disable-pip-version-check
