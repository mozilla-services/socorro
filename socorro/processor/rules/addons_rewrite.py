# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib.transform_rules import Rule


class AddonsRewriteRule(Rule):
    """Rewrite the `addons` field so make it easier to query.

    The `addons` field contains a list of add-on ids and versions, but it
    doesn't associate those. That makes it hard to query with tools like
    Elasticsearch. We thus rewrite that field so ids and versions are in a
    single string, separated by a colon.

    In case the original list of add-ons has an odd number of elements, we
    keep the last element as is.

    For example:

    >>> processed_crash['addons'] = [
    ...     'addon_1', '12.0',
    ...     'mySuperADDON', '1.143.2',
    ...     '{xws2r28dsoqq}', '42'
    ... ]
    >>> AddonsRewriteRule().act({}, {}, processed_crash, {})
    >>> print(processed_crash['addons'])
    ['addon_1:12.0', 'mySuperADDON:1.143.2', '{xws2r28dsoqq}:42']

    """

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        """Verify that the `addons` field is present in the processed_crash
        and that it is exploitable. """
        return (
            'addons' in processed_crash and
            isinstance(processed_crash['addons'], (tuple, list)) and
            len(processed_crash['addons']) > 1
        )

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        """Transform the `addons` field into a list of 'id:version' elements.
        """
        old_addons = processed_crash['addons']
        new_addons = []

        parts_nb = len(old_addons)

        for i in range(0, parts_nb, 2):
            if i + 1 == parts_nb:
                # This is the last element of a list with an odd number of
                # elements. We add it solo so as to not lose data.
                new_addons.append(old_addons[i])
            else:
                new_addons.append('%s:%s' % (old_addons[i], old_addons[i + 1]))

        processed_crash['addons'] = new_addons
        return True
