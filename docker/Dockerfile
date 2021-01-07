FROM mozilla/socorro-minidump-stackwalk:2020.09.17@sha256:9dfb090455c06c59f0ea574c0b41c9d6973be706c63ed31b099c0989a850235b as breakpad

FROM python:3.9.1-slim@sha256:56d9bdc243bc53d4bb055305b58cc0be15b05cc09dcda9b9d5e224233889b61b

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

# Copy stackwalk bits from mozilla/socorro-minidump-stackwalk image
COPY --from=breakpad /stackwalk/* /stackwalk/

# Install frontend JS deps
COPY ./webapp-django/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

# Install Socorro Python requirements
COPY --chown=app:app requirements.txt /app/
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements.txt && \
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
