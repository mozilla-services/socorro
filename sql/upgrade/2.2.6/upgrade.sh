#!/bin/bash

set -e
date

echo 'add new support functions'
psql -f fix_edit_product_info.sql breakpad

echo '2.2.6. upgrade done'

date

exit 0
