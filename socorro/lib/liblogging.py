# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import logging.config
import os
import socket


def set_up_logging(
    local_dev_env=False,
    logging_level="INFO",
    host_id=socket.gethostname(),
):
    """Initialize Python logging."""

    class AddHostID(logging.Filter):
        def filter(self, record):
            record.host_id = host_id
            return True

    class AddProcessName(logging.Filter):
        process_name = os.environ.get("PROCESS_NAME", "main")

        def filter(self, record):
            record.processname = self.process_name
            return True

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "add_hostid": {"()": AddHostID},
            "add_processname": {"()": AddProcessName},
        },
        "formatters": {
            "socorroapp": {
                "format": (
                    "%(asctime)s %(levelname)s - %(processname)s - "
                    "%(name)s - %(threadName)s - %(message)s"
                ),
            },
            "mozlog": {
                "()": "dockerflow.logging.JsonLogFormatter",
                "logger_name": "socorro",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "socorroapp",
                "filters": ["add_processname"],
            },
            "mozlog": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "mozlog",
                "filters": ["add_hostid", "add_processname"],
            },
        },
    }

    if local_dev_env:
        # In a local development environment, we don't want to see mozlog
        # format at all, but we do want to see markus things and py.warnings.
        # So set the logging up that way.
        logging_config["loggers"] = {
            "fillmore": {"handlers": ["mozlog"], "level": logging.ERROR},
            "markus": {"handlers": ["console"], "level": logging.INFO},
            "socorro": {"handlers": ["console"], "level": logging_level},
            "py.warnings": {"handlers": ["console"]},
        }

    else:
        # In a server environment, we want to use mozlog format.
        logging_config["loggers"] = {
            "fillmore": {"handlers": ["mozlog"], "level": logging.ERROR},
            "markus": {"handlers": ["console"], "level": logging.ERROR},
            "socorro": {"handlers": ["mozlog"], "level": logging_level},
        }

    logging.config.dictConfig(logging_config)
