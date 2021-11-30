# =========================================================================
# Dokcer image with minidump-stackwalk
# =========================================================================

# https://hub.docker.com/r/mozilla/socorro-minidump-stackwalk
FROM mozilla/socorro-minidump-stackwalk:2021.09.20@sha256:11dab7a81b6ff64ac16276ff1b1bd901b66cf61dce6cbfe1fbeb52b3508ac4d0 as breakpad
RUN ls -al /stackwalk/


# =========================================================================
# Dokcer image with https://github.com/luser/rust-minidump
# =========================================================================

# https://hub.docker.com/_/rust/
FROM rust:1.56.1-buster@sha256:16071065e8ad59bf5a4ee3695b4fff8f463c858e1cf5c2cb5091ab14d1309a6d as rustminidump

RUN update-ca-certificates
ARG groupid=10001
ARG userid=10001

WORKDIR /app/

RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app && \
    chown app:app /app/

USER app

# From: https://github.com/luser/rust-minidump
ARG MINIDUMPREV=5069ee30611c06ca7672f74cbfa055b089c84880
ARG MINIDUMPREVDATE=2021-11-30

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
FROM python:3.9.7-slim@sha256:cd1045dbabff11dab74379e25f7974aa7638bc5ad46755d67d0f1f1783aee101

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

# Copy stackwalk bits from mozilla/socorro-minidump-stackwalk image
COPY --from=breakpad /stackwalk/* /stackwalk/

# Copy stackwalk bits from rust-minidump minidump-stackwalker; this picks
# up minidump-stackwalk.sha as well
COPY --from=rustminidump /app/bin/* /stackwalk-rust/

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

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp-django/ && SECRET_KEY=fakekey python manage.py collectstatic --noinput

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/bin/entrypoint.sh"]
