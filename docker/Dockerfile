FROM python:3.6.7-slim-jessie

# Set up user and group
ARG groupid=10001
ARG userid=10001

WORKDIR /app/
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app

# Install OS-level things
COPY ./docker/set_up_ubuntu.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh

# Install breakpad and stackwalk bits
COPY ./scripts/build-breakpad.sh /tmp/scripts/
COPY ./scripts/build-stackwalker.sh /tmp/scripts/
COPY ./minidump-stackwalk/ /tmp/minidump-stackwalk/
RUN STACKWALKDIR=/stackwalk SRCDIR=/tmp /tmp/scripts/build-stackwalker.sh

# Install frontend JS deps
COPY ./webapp-django/package.json /webapp-frontend-deps/package.json
COPY ./webapp-django/package-lock.json /webapp-frontend-deps/package-lock.json
RUN cd /webapp-frontend-deps/ && npm install

# Install crontabber JS deps
COPY ./crontabber/package.json /crontabber-deps/package.json
COPY ./crontabber/package-lock.json /crontabber-deps/package-lock.json
RUN cd /crontabber-deps/ && npm install

# Install Socorro Python requirements
COPY ./requirements /app/requirements
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements/default.txt -c requirements/constraints.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app

ENV WEBPACK_BINARY /webapp-frontend-deps/node_modules/.bin/webpack
ENV LESS_BINARY /webapp-frontend-deps/node_modules/.bin/lessc
ENV UGLIFYJS_BINARY /webapp-frontend-deps/node_modules/.bin/uglifyjs
ENV CSSMIN_BINARY /webapp-frontend-deps/node_modules/.bin/cssmin
ENV NPM_ROOT_PATH /webapp-frontend-deps/
ENV NODE_PATH /webapp-frontend-deps/node_modules/

# Copy everything over
COPY . /app/

# Build webpack-defined frontend bundles
RUN cd /app/webapp-django/ && $WEBPACK_BINARY --mode=production --bail

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp-django/ && python manage.py collectstatic --noinput

USER app

# Build tmp directories for minidump stackwalker--owned by app
RUN mkdir -p /tmp/symbols/cache
RUN mkdir -p /tmp/symbols/tmp

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/docker/socorro_entrypoint.sh"]
