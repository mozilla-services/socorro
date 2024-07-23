# Socorro Code Graveyard

This document records interesting code that we've deleted for the sake of discoverability for the future.

## Various scripts

* [Removal PR](https://github.com/mozilla-services/socorro/pull/6674)

`bin/remove_field.py` which removes fields from raw crashes in crash storage and elasticsearch.

`bin/load_processed_crashes_into_es.py` which was used to backfill elasticsearch from crash storage
when migrating to Google Cloud Platform.

## S3 and SQS support

* [Removal PR](https://github.com/mozilla-services/socorro/pull/6669)

S3 crash storage and sqs crash queue support were removed after migrating to Google Cloud Platform.
