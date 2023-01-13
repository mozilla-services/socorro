# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io

from django.core.management import call_command
from django.utils import timezone


class TestEsclean:
    def test_esclean(self, db, es_conn):
        """Test deleting expired indices."""
        # Create some old indices
        es_conn.create_index("testsocorro201801")
        es_conn.create_index("testsocorro201802")
        # Create an index for this week
        this_week = timezone.now().strftime(es_conn.config.elasticsearch_index)
        es_conn.create_index(this_week)
        es_conn.health_check()

        out = io.StringIO()
        call_command("esclean", stdout=out)
        assert out.getvalue() == (
            "Deleting expired crash report indices.\n"
            "Deleting testsocorro201801\n"
            "Deleting testsocorro201802\n"
        )
