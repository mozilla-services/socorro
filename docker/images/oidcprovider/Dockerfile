FROM mozilla/oidc-testprovider:oidc_testprovider-v0.10.10

# Modify redirect_urls specified in "fixtures.json" to fit our needs.
COPY fixtures.json /code/fixtures.json

CMD ["./bin/run.sh"]
