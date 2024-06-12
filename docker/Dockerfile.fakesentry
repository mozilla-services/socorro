FROM python:3.11.9-slim-bullseye@sha256:320da7887b542fee80af7fac52146047a980d767abb9b8fe69d86eaa9113bcc4

ARG groupid=5000
ARG userid=5000

WORKDIR /app/

RUN groupadd -r kent && useradd --no-log-init -r -g kent kent

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl tini && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir 'kent==2.0.0'

USER kent

ENTRYPOINT ["tini", "--", "/usr/local/bin/kent-server"]
CMD ["run"]
