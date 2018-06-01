# Derived from the "testprovider" container from
# https://github.com/mozilla-parsys/docker-test-mozilla-django-oidc.
# Only the redirect_urls specified in "fixtures.json" are being
# modified to fit the needs of the docker setup.

FROM mozillaparsys/oidc_testprovider

COPY ./docker/config/oidcprovider-fixtures.json /code/fixtures.json
