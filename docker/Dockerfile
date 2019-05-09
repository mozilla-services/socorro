FROM python:3.6.8-slim-stretch as socorro_image_base

# Set up user and group
ARG groupid=10001
ARG userid=10001

WORKDIR /app/
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app

# Install OS-level things
COPY ./docker/set_up_ubuntu.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh


FROM socorro_image_base as socorro_breakpad

WORKDIR /mdsw/

# Install some helpful debugging things
RUN apt-get -y install gdb vim

# Build breakpad client and stackwalker binaries
COPY ./scripts/build-breakpad.sh /mdsw/scripts/
COPY ./scripts/build-stackwalker.sh /mdsw/scripts/
COPY ./minidump-stackwalk/ /mdsw/minidump-stackwalk/
RUN STACKWALKDIR=/stackwalk SRCDIR=/mdsw /mdsw/scripts/build-stackwalker.sh

# Let app own /mdsw and /stackwalk so it's easier to debug later
RUN chown -R app.app /mdsw
RUN chown -R app.app /stackwalk

FROM socorro_image_base
WORKDIR /app/

# Copy stackwalk bits
COPY --from=socorro_breakpad /stackwalk/* /stackwalk/

# Install frontend JS deps
COPY ./webapp-django/package.json /webapp-frontend-deps/package.json
COPY ./webapp-django/package-lock.json /webapp-frontend-deps/package-lock.json
RUN cd /webapp-frontend-deps/ && npm install

# Install Socorro Python requirements
COPY ./requirements /app/requirements
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements/default.txt -c requirements/constraints.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app

ENV LESS_BINARY /webapp-frontend-deps/node_modules/.bin/lessc
ENV UGLIFYJS_BINARY /webapp-frontend-deps/node_modules/.bin/uglifyjs
ENV CSSMIN_BINARY /webapp-frontend-deps/node_modules/.bin/cssmin
ENV NPM_ROOT_PATH /webapp-frontend-deps/
ENV NODE_PATH /webapp-frontend-deps/node_modules/

# Copy everything over
COPY . /app/

# Run collectstatic in container which puts files in the default place for
# static files
RUN cd /app/webapp-django/ && python manage.py collectstatic --noinput

# app should own everything under /app in the container
RUN chown -R app.app /app

USER app

# Build tmp directories for minidump stackwalker
RUN mkdir -p /tmp/symbols/cache
RUN mkdir -p /tmp/symbols/tmp

# Set entrypoint for this image. The entrypoint script takes a service
# to run as the first argument. See the script for available arguments.
ENTRYPOINT ["/app/docker/socorro_entrypoint.sh"]
