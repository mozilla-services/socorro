# =========================================================================
# Building app image
# =========================================================================

# https://hub.docker.com/_/python
FROM python:3.9.18-slim-bookworm@sha256:08a6a1666ddebe94becbec1986235cb8c321d2f7a7fd00f614befba5c1f23e67

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

# Install frontend JS deps
COPY --chown=app:app ./webapp/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

COPY --chown=app:app requirements.txt /app/
RUN pip install -U 'pip==22.3.1' && \
    pip install --no-cache-dir --no-deps -r requirements.txt && \
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

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp/ && TOOL_ENV=True python manage.py collectstatic --noinput

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/bin/entrypoint.sh"]
