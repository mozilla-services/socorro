#! /bin/bash -e

# Create a new socorro user
set +e
grep socorro /etc/passwd 2>&1 > /dev/null
if [ $? -ne 0 ]; then
    useradd -m socorro 2> /dev/null
fi
set -e
