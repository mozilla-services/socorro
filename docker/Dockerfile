FROM python:2.7.13-slim

WORKDIR /app/
RUN groupadd --gid 10001 app && useradd -g app --uid 10001 --shell /usr/sbin/nologin app

# Install OS-level things
COPY ./docker/set_up_ubuntu.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up_ubuntu.sh

# Install Socorro Python requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app
