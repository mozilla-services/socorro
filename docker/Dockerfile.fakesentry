FROM python:3.10.8-alpine3.16@sha256:d17cfece24cb5d0432b37c138f307a19dd461b88aded1fc6981ef5c997c74de1

ARG groupid=5000
ARG userid=5000

WORKDIR /app/

RUN addgroup -g $groupid app && \
    adduser --disabled-password --gecos "" --home /home/app --ingroup app --uid $userid app && \
    chown app:app /app/

RUN apk add --no-cache tini

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir 'kent==1.0.0'

USER app

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/kent-server"]
CMD ["run"]
