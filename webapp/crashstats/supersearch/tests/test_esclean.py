# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import io

from django.core.management import call_command


class TestEsclean:
    def test_esclean(self, db, preferred_es_helper):
        """Test deleting expired indices."""
        original_indexes = list(sorted(preferred_es_helper.get_indices()))

        # Create some old indices
        template = preferred_es_helper.get_index_template()

        old_index1 = datetime.date(2018, 1, 1).strftime(template)
        preferred_es_helper.create_index(old_index1)
        old_index2 = datetime.date(2019, 1, 1).strftime(template)
        preferred_es_helper.create_index(old_index2)

        preferred_es_helper.health_check()

        assert (
            preferred_es_helper.get_indices()
            == [old_index1, old_index2] + original_indexes
        )

        out = io.StringIO()
        call_command("esclean", stdout=out)
        assert out.getvalue() == (
            "Deleting expired crash report indices.\n"
            + f"Deleting {old_index1}\n"
            + f"Deleting {old_index2}\n"
        )

        assert preferred_es_helper.get_indices() == original_indexes
