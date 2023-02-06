# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib


def import_class(class_path):
    modpath, name = class_path.rsplit(".", 1)
    module = importlib.import_module(modpath)
    return getattr(module, name)


def build_instance(class_path, kwargs):
    cls = import_class(class_path)
    return cls(**kwargs)


def build_instance_from_settings(value):
    class_path = value["class"]
    kwargs = value.get("options", {})
    return build_instance(class_path, kwargs)
