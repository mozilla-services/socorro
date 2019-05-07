# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import collections


def dotdict_to_dict(sdotdict):
    """Takes a DotDict and returns a dict

    This does a complete object traversal converting all instances of the
    things named DotDict to dict so it's deep-copyable.

    """
    def _dictify(thing):
        if isinstance(thing, collections.Mapping):
            return dict([(key, _dictify(val)) for key, val in thing.items()])
        elif isinstance(thing, str):
            # NOTE(willkg): Need to do this because strings are sequences but
            # we don't want to convert them into lists in the next clause
            return thing
        elif isinstance(thing, collections.Sequence):
            return [_dictify(item) for item in thing]
        return thing

    return _dictify(sdotdict)
