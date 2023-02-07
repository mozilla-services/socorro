# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import contextlib
import importlib
import logging
import re
import os


LOGGER = logging.getLogger(__name__)


UPPER_CASE_KEY_RE = re.compile(r"^[A-Z][A-Z_]+$")


class Settings:
    def __init__(self, settings_module_path):
        self._settings_module_path = settings_module_path

        settings_module = importlib.import_module(settings_module_path)
        for key in dir(settings_module):
            if not UPPER_CASE_KEY_RE.match(key):
                continue
            setattr(self, key, getattr(settings_module, key))

    def log_settings(self, logger=LOGGER):
        """Log settings making sure to sanitize values that have "secret" in the key"""

        def sanitize_value(k, v):
            if "secret" in k.lower():
                return "***** (secret)"

            if isinstance(v, (tuple, list)):
                return type(v)([sanitize_value(k, v_item) for v_item in v])

            if isinstance(v, dict):
                return {
                    sub_k: sanitize_value(sub_k, sub_v) for sub_k, sub_v in v.items()
                }
            return v

        for key in dir(self):
            if not UPPER_CASE_KEY_RE.match(key):
                continue
            value = sanitize_value(key, getattr(self, key))

            logger.info("%s: %r", key, value)

    def __repr__(self):
        return f"<Settings {self._settings_module_path!r}>"

    @contextlib.contextmanager
    def override(self, key, value):
        """Override settings for testing

        :arg key: the key to override
        :arg value: the value to override with

        """
        NOVALUE = object()

        if not UPPER_CASE_KEY_RE.match(key):
            raise ValueError(f"Invalid key {key!r}")

        old_value = getattr(self, key, NOVALUE)
        setattr(self, key, value)
        try:
            yield

        finally:
            if old_value is NOVALUE:
                with contextlib.suppress(AttributeError):
                    delattr(self, key)
            else:
                setattr(self, key, old_value)


def __load_settings():
    # Get settings module defaulting to "socorro.mozilla_settings"
    settings_module_path = os.environ.get(
        "SOCORRO_SETTINGS", "socorro.mozilla_settings"
    )
    if not settings_module_path:
        raise Exception(
            "SOCORRO_SETTINGS environment variable not specified. "
            + "It must be a dotted path to the settings module."
        )

    return Settings(settings_module_path)


settings = __load_settings()
