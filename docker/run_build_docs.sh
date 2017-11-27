#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

cd docs

# Copy the e2e-test README to this directory because otherwise we can't
# pull it in because there isn't a way to do a file include for Markdown
# files.
cp ../e2e-tests/README.md tests/e2e_readme.md

# Build the docs
make html
