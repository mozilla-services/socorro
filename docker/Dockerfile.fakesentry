FROM python:3.10.5-alpine3.16@sha256:52ce18e9d7a2556a3632d093f8f77700307735b7e7049dce3339c9bf9221ae7f

ARG groupid=5000
ARG userid=5000

WORKDIR /app/

RUN addgroup -g $groupid app && \
    adduser --disabled-password --gecos "" --home /home/app --ingroup app --uid $userid app && \
    chown app:app /app/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install -U 'pip>=20' && \
    pip install --no-cache-dir 'kent==0.5.0'

USER app

ENTRYPOINT ["/usr/local/bin/kent-server"]
CMD ["run"]
