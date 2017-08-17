#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Install aws cli as the current user in /tmp so it doesn't interfere with
# socorro/system requirements
HOME=/tmp pip install awscli --user

# Fix permissions so anyone can use it
find /tmp/.local/ -type d -exec '/bin/chmod' '755' '{}' ';'
find /tmp/.local/ -type f -exec '/bin/chmod' '644' '{}' ';'
chmod 755 /tmp/.local/bin/*
