# This should be kept in sync with the python version used in docker/Dockerfile
FROM --platform=linux/amd64 mcr.microsoft.com/devcontainers/python:3.11-bookworm@sha256:48ded8da0748a85a4f37fbf5383c31f4893438fe76b1e11a0698c6965bea61a1 AS devcontainer_amd64

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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    NPM_ROOT_PATH=/app/webapp/ \
    NODE_PATH=/app/webapp/node_modules/

# Install frontend JS deps
COPY --chown=app:app ./webapp/package*.json /app/webapp/
RUN cd /app/webapp/ && npm ci

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

USER app

# Install Python dependencies
RUN --mount=type=cache,uid=$userid,gid=$groupid,target=/home/app/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --group devcontainer
ENV PATH="/app/.venv/bin:$PATH"
