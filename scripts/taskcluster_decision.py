#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from os.path import dirname

import requests
from taskcluster import fromNow
from taskcluster.utils import stableSlugId, dumpJson


ROOT = dirname(dirname(__file__))
BASE_URL = 'http://taskcluster/queue/v1'


def main():
    _idMaker = stableSlugId()

    def idMaker(name):
        return _idMaker(name).decode()

    with open(os.path.join(ROOT, 'breakpad_rev.txt')) as f:
        breakpad_rev = f.read()

    breakpad_task = {
        'metadata': {
            'name': 'socorro:build_breakpad',
            'description': 'Build Breakpad for Socorro consumption',
            'owner': os.environ['GITHUB_HEAD_USER_EMAIL'],
            'source': os.environ['GITHUB_HEAD_REPO_URL'],
        },
        'provisionerId': 'aws-provisioner-v1',
        'workerType': 'gecko-misc',
        'schedulerId': 'taskcluster-github',
        'taskGroupId': os.environ['TASK_ID'],
        'created': fromNow('0 seconds'),
        'deadline': fromNow('1 day'),
        'expires': fromNow('365 days'),
        'routes': [
            'index.project.socorro.breakpad.v1.builds.linux64.%s' % breakpad_rev,
        ],
        'scopes': [
            'index.project.socorro.breakpad.v1.builds.linux64.%s' % breakpad_rev,
        ],
        'payload': {
            'image': 'taskcluster/desktop-build:0.1.11',
            'command': [
                '/bin/bash',
                '-c',
                ' && '.join([
                    'apt-get update',
                    'apt-get install -y git',
                    'cd ~',
                    'git clone $GITHUB_HEAD_REPO_URL socorro',
                    'pushd socorro',
                    'git checkout $GITHUB_HEAD_SHA',
                    'popd',
                    'source ~/socorro/scripts/breakpad-taskcluster.sh',
                    '~/socorro/scripts/build-breakpad.sh'
                ])
            ],
            'maxRunTime': 28800,  # 8 hours
            'artifacts': {
                'public/breakpad.tar.gz': {
                    'type': 'file',
                    'path': '/home/worker/breakpad.tar.gz',
                },
            },
            'features': {
                'taskclusterProxy': True,
            },
        },
    }

    task_id = idMaker(breakpad_task['name'])
    res = requests.put('%s/task/%s' % (BASE_URL, task_id), data=dumpJson(breakpad_task))
    print(res.text)
    res.raise_for_status()


if __name__ == '__main__':
    main()
