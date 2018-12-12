# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


def _default_list_splitter(class_list_str):
    return [x.strip() for x in class_list_str.split(',') if x.strip()]


def _default_class_extractor(list_element):
    return list_element


def change_default(
    kls,
    key,
    new_default,
    new_converter=None,
    new_reference_value=None,
):
    """return a new configman Option object that is a copy of an existing one,
    giving the new one a different default value"""
    an_option = kls.get_required_config()[key].copy()
    an_option.default = new_default
    if new_converter:
        an_option.from_string_converter = new_converter
    if new_reference_value:
        an_option.reference_value_from = new_reference_value
    return an_option
