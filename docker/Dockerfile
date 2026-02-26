# =========================================================================
# Building app image
# =========================================================================

# https://hub.docker.com/_/python
# NOTE(smarnach): To upgrade Python to a new minor or major version, see
# https://socorro.readthedocs.io/en/latest/dev.html#upgrading-to-a-new-python-version
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim@sha256:4f5d923c9dcea037f57bda425dd209f3ec643da2f0b74227f68d09dab0b3bb36

# Set up user and group
ARG groupid=10001
ARG userid=10001

WORKDIR /app/

# Install OS-level things
COPY docker/set_up_ubuntu.sh /tmp/set_up_ubuntu.sh
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app && \
    chown app:app /app/ && \
    DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh && \
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

# app should own everything under /app in the container
USER app

# Install Python dependencies
RUN --mount=type=cache,uid=$userid,gid=$groupid,target=/home/app/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked
ENV PATH="/app/.venv/bin:$PATH"

# Copy everything over
COPY --chown=app:app . /app/

# Build front-end static files. Runs ESBuild and collectstatic
RUN cd /app/webapp/ && npm run build

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/bin/entrypoint.sh"]
