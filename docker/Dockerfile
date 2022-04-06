# =========================================================================
# Dokcer image with https://github.com/luser/rust-minidump
# =========================================================================

# https://hub.docker.com/_/rust/
FROM rust:1.59.0-buster@sha256:80f2e747f4d6b572e79b845df87b47dd9102f236113efd8921a115f4515b7df1 as rustminidump

ARG groupid=10001
ARG userid=10001

WORKDIR /app/

RUN update-ca-certificates && \
    groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app && \
    chown app:app /app/

USER app

# From: https://github.com/luser/rust-minidump
ARG MINIDUMPREV=e954907c9f5a69037df459cacb4d0846b0599479
ARG MINIDUMPREVDATE=2022-03-23

RUN cargo install --locked --root=/app/ \
    --git https://github.com/rust-minidump/rust-minidump.git \
    --rev $MINIDUMPREV \
    minidump-stackwalk
RUN echo "{\"sha\":\"$MINIDUMPREV\",\"date\":\"$MINIDUMPREVDATE\"}" > /app/bin/minidump-stackwalk.version.json
RUN ls -al /app/bin/


# =========================================================================
# Building app image
# =========================================================================

# https://hub.docker.com/_/python
FROM python:3.9.12-slim@sha256:131e182eea705eaea14d915829e498da4dd77e0dd3882a04d8e0bffea9efeb69

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
