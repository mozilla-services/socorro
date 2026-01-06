FROM mozilla/oidc-testprovider:oidc_testprovider-0.10.12

# Modify redirect_urls specified in "fixtures.json" to fit our needs.
COPY fixtures.json /code/fixtures.json

CMD ["./bin/run.sh"]
