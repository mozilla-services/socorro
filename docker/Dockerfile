# =========================================================================
# Building app image
# =========================================================================

# https://hub.docker.com/_/python
# NOTE(smarnach): To upgrade Python to a new minor or major version, see
# https://socorro.readthedocs.io/en/latest/dev.html#upgrading-to-a-new-python-version
FROM --platform=linux/amd64 python:3.11.11-slim-bookworm@sha256:42420f737ba91d509fc60d5ed65ed0492678a90c561e1fa08786ae8ba8b52eda AS app_amd64

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

COPY --chown=app:app requirements.txt /app/
RUN pip install --no-cache-dir --no-deps -r requirements.txt && \
    pip check --disable-pip-version-check

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UGLIFYJS_BINARY=/webapp-frontend-deps/node_modules/.bin/uglifyjs \
    CSSMIN_BINARY=/webapp-frontend-deps/node_modules/.bin/cssmin \
    NPM_ROOT_PATH=/webapp-frontend-deps/ \
    NODE_PATH=/webapp-frontend-deps/node_modules/

# Install frontend JS deps
COPY --chown=app:app ./webapp/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

# app should own everything under /app in the container
USER app

# Copy everything over
COPY --chown=app:app . /app/

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp/ && TOOL_ENV=True python manage.py collectstatic --noinput

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/bin/entrypoint.sh"]
