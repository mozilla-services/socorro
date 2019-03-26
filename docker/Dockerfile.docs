FROM python:3.6.8-slim-stretch

ARG groupid=10001
ARG userid=10001

WORKDIR /app/
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin app

# Install graphviz
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y graphviz make

# Install docs-building requirements
COPY ./docs/requirements.txt /tmp
RUN pip install -U 'pip>=8' && \
    pip install -r /tmp/requirements.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app
