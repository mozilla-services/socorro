# Generated by Django 1.11.16 on 2018-11-18 02:56

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import migrations


def add_major_version(apps, schema_editor):
    ProductVersion = apps.get_model("crashstats", "ProductVersion")

    for pv in ProductVersion.objects.all():
        version = pv.release_version
        major_version = version.split(".")[0]
        pv.major_version = int(major_version)
        pv.save()


def zero_major_version(apps, schema_editor):
    # This doesn't "undo" the major version, but it does zero it out
    ProductVersion = apps.get_model("crashstats", "ProductVersion")

    for pv in ProductVersion.objects.all():
        pv.major_version = 0
        pv.save()


class Migration(migrations.Migration):
    dependencies = [("crashstats", "0012_1507916_productversion_major_version")]

    operations = [migrations.RunPython(add_major_version, zero_major_version)]
