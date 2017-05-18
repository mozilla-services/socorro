#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Installs packages and other things in an Ubuntu Docker image.

# Failures should cause setup to fail
set -v -e -x

# Update the operating system and install OS-level dependencies
apt-get update
apt-get install -y gcc apt-transport-https build-essential python-dev

# Install postgres requirements
apt-get install -y libpq-dev

# Install lxml requirements
apt-get install -y libxml2-dev libxslt1-dev

# Install sasl requirements
apt-get install -y libsasl2-dev

# Install cffi
apt-get install -y libffi-dev

# Install git
apt-get install -y git
