# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Gunicorn configuration

import logging
import socket

from decouple import config as CONFIG


LOGGING_LEVEL = CONFIG('LOGGING_LEVEL', 'INFO')
LOCAL_DEV_ENV = CONFIG('LOCAL_DEV_ENV', False, cast=bool)

HOST_ID = socket.gethostname()


class AddHostID(logging.Filter):
    def filter(self, record):
        record.host_id = HOST_ID
        return True


logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'add_hostid': {
            '()': AddHostID
        },
    },
    'handlers': {
        'console': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'socorroapp',
        },
        'mozlog': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'mozlog',
            'filters': ['add_hostid']
        },
    },
    'formatters': {
        'socorroapp': {
            'format': '%(asctime)s %(levelname)s - %(name)s - %(message)s',
        },
        'mozlog': {
            '()': 'dockerflow.logging.JsonLogFormatter',
            'logger_name': 'socorro'
        },
    },
}

if LOCAL_DEV_ENV:
    # In a local development environment, we don't want to see mozlog
    # format at all, but we do want to see markus things and py.warnings.
    # So set the logging up that way.
    logconfig_dict['loggers'] = {
        'gunicorn': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
        }
    }
else:
    # In a server environment, we want to use mozlog format.
    logconfig_dict['loggers'] = {
        'gunicorn': {
            'handlers': ['mozlog'],
            'level': LOGGING_LEVEL,
        }
    }
