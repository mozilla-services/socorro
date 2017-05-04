FROM python:2.7.13-slim

WORKDIR /app/
RUN groupadd --gid 10001 app && useradd -g app --uid 10001 --shell /usr/sbin/nologin app

# Install OS-level things
COPY ./docker/set_up_ubuntu.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh

# Install breakpad bits
COPY ./scripts/build-breakpad.sh /tmp
COPY ./minidump-stackwalk/ /tmp/minidump-stackwalk/
COPY ./docker/set_up_stackwalk.sh /tmp
RUN /tmp/set_up_stackwalk.sh

# Install Socorro Python requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements.txt

# This is relative to docker/base/Dockerfile
COPY . /app/

# Install Socorro in the container so we pick up the console script
RUN cd /app/ && pip install -e .

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

USER app
