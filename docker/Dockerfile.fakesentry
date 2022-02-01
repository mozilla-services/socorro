FROM python:3.10.1-alpine3.15@sha256:affe0faa14e7553fc570beec3864e74b5e36f8c19b2bb49ae8ba79c0e9e7236e

ARG groupid=5000
ARG userid=5000

WORKDIR /app/

RUN addgroup -g $groupid app && \
    adduser --disabled-password --gecos "" --home /home/app --ingroup app --uid $userid app && \
    chown app:app /app/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir 'kent==0.4.0'

USER app

ENTRYPOINT ["/usr/local/bin/kent-server"]
CMD ["run"]
