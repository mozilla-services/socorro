#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: docker/set_up_ubuntu.sh
#
# Installs packages and other things in an Ubuntu Docker image.

set -euo pipefail

# Update the operating system and install OS-level dependencies
apt-get update

PACKAGES_TO_INSTALL=(
    apt-transport-https

    # For building Python libraries
    build-essential
    libpq-dev
    libxml2-dev libxslt1-dev
    libsasl2-dev
    libffi-dev

    # For scripts
    git

    # For running services
    tini

    # For nodejs and npm
    curl

    # For database maintenance
    postgresql-client
)

# Install Ubuntu packages
apt-get install -y "${PACKAGES_TO_INSTALL[@]}"

# Install nodejs and npm from Nodesource's 14.x branch
curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -
echo 'deb https://deb.nodesource.com/node_18.x buster main' > /etc/apt/sources.list.d/nodesource.list
echo 'deb-src https://deb.nodesource.com/node_18.x buster main' >> /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y nodejs

# Remove apt cache
rm -rf /var/lib/apt/lists/*

# Stomp on the bash prompt with something more useful
cat > /etc/bash.bashrc <<EOF
# Get the name for the current uid.
MYUSER="\$(id -u -n)"

# Set the prompt to use the username we just figured out plus the container
# name which is in an environment variable. If there is no CONTAINERNAME,
# then use the host name.
PS1="\${MYUSER}@socorro:\\w\$ "

# Add current directory to path.
PATH=\${PATH}:.
EOF

# Remove this bashrc so it doesn't override the global one we created
rm /home/app/.bashrc
