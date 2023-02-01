# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models, migrations
import crashstats.tokens.models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Token",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        default=crashstats.tokens.models.make_key, max_length=32
                    ),
                ),
                (
                    "expires",
                    models.DateTimeField(default=crashstats.tokens.models.get_future),
                ),
                ("notes", models.TextField(blank=True)),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("permissions", models.ManyToManyField(to="auth.Permission")),
                (
                    "user",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
