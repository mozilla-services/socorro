# Socorro Code Graveyard

This document records interesting code that we've deleted for the sake of discoverability for the future.

## Various scripts

* [Removal PR](https://github.com/mozilla-services/socorro/pull/6674)

`bin/remove_field.py` which removes fields from raw crashes in crash storage and elasticsearch.

`bin/load_processed_crashes_into_es.py` which was used to backfill elasticsearch from crash storage
when migrating to Google Cloud Platform.

* [Removal PR](https://github.com/mozilla-services/socorro/pull/6814)

`webapp/less_to_css.sh` which converts LESS files to CSS, with associated NPM script `"convert:less": "sh less_to_css.sh"`

## S3 and SQS support

* [Removal PR](https://github.com/mozilla-services/socorro/pull/6669)

S3 crash storage and sqs crash queue support were removed after migrating to Google Cloud Platform.
