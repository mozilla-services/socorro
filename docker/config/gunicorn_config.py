# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Gunicorn configuration

import logging
import socket

from decouple import config as CONFIG


LOGGING_LEVEL = CONFIG("LOGGING_LEVEL", "INFO")
LOCAL_DEV_ENV = CONFIG("LOCAL_DEV_ENV", False, cast=bool)
HOST_ID = socket.gethostname()


class AddHostID(logging.Filter):
    def filter(self, record):
        record.host_id = HOST_ID
        return True


logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"add_hostid": {"()": AddHostID}},
    "handlers": {
        "console": {
            "level": LOGGING_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "socorroapp",
        },
        "mozlog": {
            "level": LOGGING_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "mozlog",
            "filters": ["add_hostid"],
        },
    },
    "formatters": {
        "socorroapp": {"format": "%(asctime)s %(levelname)s - %(name)s - %(message)s"},
        "mozlog": {
            "()": "dockerflow.logging.JsonLogFormatter",
            "logger_name": "socorro",
        },
    },
    "loggers": {
        "gunicorn": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
        "gunicorn.error": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
    },
    "root": {"handlers": ["mozlog"], "level": LOGGING_LEVEL},
}

if LOCAL_DEV_ENV:
    # In a local development environment, we want to use console logger.
    for logger, logger_config in logconfig_dict["loggers"].items():
        logger_config["handlers"] = ["console"]
    logconfig_dict["root"]["handlers"] = ["console"]
