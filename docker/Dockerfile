# =========================================================================
# Dokcer image with https://github.com/luser/rust-minidump
# =========================================================================

# https://hub.docker.com/_/rust/
FROM rust:1.58.1-buster@sha256:311d05f3823e7430bfeb2a743cd1a7895b05db643622d8d38ce18bffa2fa63bf as rustminidump

RUN update-ca-certificates
ARG groupid=10001
ARG userid=10001

WORKDIR /app/

RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app && \
    chown app:app /app/

USER app

# From: https://github.com/luser/rust-minidump
ARG MINIDUMPREV=1c5f5f81f4431f358d5342c7e1114b0737949474
ARG MINIDUMPREVDATE=2022-01-20

RUN cargo install --locked --root=/app/ \
    --git https://github.com/luser/rust-minidump.git \
    --rev $MINIDUMPREV \
    minidump-stackwalk
RUN echo "{\"sha\":\"$MINIDUMPREV\",\"date\":\"$MINIDUMPREVDATE\"}" > /app/bin/minidump-stackwalk.version.json
RUN ls -al /app/bin/


# =========================================================================
# Building app image
# =========================================================================

# https://hub.docker.com/_/python
FROM python:3.10.2-slim@sha256:2d2dd5235df5b831a35438b9537f9147c6588cb802f53720d6c5a473d175ffb1

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
RUN rm /tmp/set_up_ubuntu.sh

# Copy stackwalk bits from rust-minidump minidump-stackwalker; this picks
# up minidump-stackwalk.sha as well
COPY --from=rustminidump /app/bin/* /stackwalk-rust/

# Install frontend JS deps
COPY ./webapp-django/package*.json /webapp-frontend-deps/
RUN cd /webapp-frontend-deps/ && npm install

COPY --chown=app:app requirements.txt /app/
RUN pip install -U 'pip>=20' && \
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

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp-django/ && SECRET_KEY=fakekey python manage.py collectstatic --noinput

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/bin/entrypoint.sh"]
