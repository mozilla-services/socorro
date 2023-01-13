# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is a no-op data migration. If you need to do the data
# migration, do it with SQL.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("crashstats", "0004_1463121-signature")]

    operations = []
