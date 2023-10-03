# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Generated by Django 1.11.11 on 2018-05-22 15:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("status", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="statusmessage",
            name="severity",
            field=models.CharField(
                choices=[
                    (b"info", b"Info"),
                    (b"warning", b"Warning"),
                    (b"critical", b"Critical"),
                ],
                max_length=20,
            ),
        )
    ]
