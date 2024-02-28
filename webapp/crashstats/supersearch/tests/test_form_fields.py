# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

import pytest

from django.forms import ValidationError

from crashstats.supersearch import form_fields


class TestIntegerField:
    def test_gt(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean([">13"])
        assert cleaned_value == [13]
        assert field.prefixed_value == [">13"]

    def test_duplicate(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean(["<10", "<10"])
        assert cleaned_value == [10, 10]
        assert field.prefixed_value == ["<10", "<10"]

    def test_not(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean(["!13"])
        assert cleaned_value == [13]
        assert field.prefixed_value == ["!13"]

    def test_null(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean(["__null__"])
        assert cleaned_value == ["__null__"]

    def test_not_null(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean(["!__null__"])
        assert cleaned_value == ["!__null__"]

    def test_not_null_and_filter(self):
        field = form_fields.IntegerField()
        cleaned_value = field.clean([">10", "!__null__"])
        assert cleaned_value == [10, "!__null__"]

    def test_invalid_combinations(self):
        field = form_fields.IntegerField()

        # Test non-overlapping ranges
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean([">10", "<10"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<10", ">10"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<10", ">=10"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<=10", ">10"])

        # Test doesn't exist with a filter--this is invalid
        with pytest.raises(ValidationError, match="Can't combine __null__"):
            field.clean([">10", "__null__"])
        # Test doesn't exist with a filter--this is invalid
        with pytest.raises(ValidationError, match="Can't combine __null__"):
            field.clean(["__null__", ">10"])


class TestFloatField:
    def test_gt(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean([">13.0"])
        assert cleaned_value == [13.0]
        assert field.prefixed_value == [">13.0"]

    def test_duplicate(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean(["<10.1", "<10.1"])
        assert cleaned_value == [10.1, 10.1]
        assert field.prefixed_value == ["<10.1", "<10.1"]

    def test_not(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean(["!13.2"])
        assert cleaned_value == [13.2]
        assert field.prefixed_value == ["!13.2"]

    def test_null(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean(["__null__"])
        assert cleaned_value == ["__null__"]

    def test_not_null(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean(["!__null__"])
        assert cleaned_value == ["!__null__"]

    def test_not_null_and_filter(self):
        field = form_fields.FloatField()
        cleaned_value = field.clean([">10.55", "!__null__"])
        assert cleaned_value == [10.55, "!__null__"]

    def test_invalid_combinations(self):
        field = form_fields.FloatField()

        # Test non-overlapping ranges
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean([">10.5", "<10.5"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<10.4", ">10.4"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<10.3", ">=10.3"])
        with pytest.raises(ValidationError, match="Operator combination failed"):
            field.clean(["<=10.2", ">10.2"])

        # Test doesn't exist with a filter--this is invalid
        with pytest.raises(ValidationError, match="Can't combine __null__"):
            field.clean([">10.4", "__null__"])
        # Test doesn't exist with a filter--this is invalid
        with pytest.raises(ValidationError, match="Can't combine __null__"):
            field.clean(["__null__", ">10.4"])


class TestDateTimeField:
    def test_gt_datetime(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">12/31/2012 10:20:30"])
        dt = datetime.datetime(2012, 12, 31, 10, 20, 30)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">2012-12-31T10:20:30+00:00"]

    def test_gte_date(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">=2012-12-31"])
        dt = datetime.datetime(2012, 12, 31)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">=2012-12-31T00:00:00+00:00"]

    def test_gte_datetime(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean([">=2012-12-31T01:02:03+00:00"])
        dt = datetime.datetime(2012, 12, 31, 1, 2, 3)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        assert cleaned_value == [dt]
        assert field.prefixed_value == [">=2012-12-31T01:02:03+00:00"]

    def test_duplicate_values(self):
        field = form_fields.DateTimeField()
        cleaned_value = field.clean(["<2016-08-10", "<2016-08-10"])
        dt = datetime.datetime(2016, 8, 10)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        assert cleaned_value == [dt, dt]

    def test_invalid_combinations(self):
        field = form_fields.DateTimeField()
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">=2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "<=2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">=2016-08-10", "<=2016-08-09"])

        # but note, this should work!
        field.clean([">=2016-08-10", "<=2016-08-10"])

        # any use of the equal sign and a less or greater than
        with pytest.raises(ValidationError):
            field.clean(["=2016-08-10", "<2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean(["=2016-08-10", ">2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean([">2016-08-10", "=2016-08-10"])
        with pytest.raises(ValidationError):
            field.clean(["<2016-08-10", "=2016-08-10"])

        # more than two fields
        with pytest.raises(ValidationError):
            field.clean([">2016-08-01", "<=2016-08-02", ">=2016-08-02"])
        with pytest.raises(ValidationError):
            field.clean(["<2016-08-01", "<2016-08-02", "<2016-08-03"])


class TestBooleanField:
    def test_none(self):
        field = form_fields.BooleanField(required=False)
        # If the input is None, leave it as None
        cleaned_value = field.clean(None)
        assert cleaned_value is None

    def test_truthy(self):
        field = form_fields.BooleanField(required=False)
        # The list of known truthy strings
        for value in form_fields.BooleanField.truthy_strings:
            cleaned_value = field.clean(value)
            assert cleaned_value == "__true__"
        # But it's also case insensitive, so check that it still works
        for value in form_fields.BooleanField.truthy_strings:
            cleaned_value = field.clean(value.upper())  # note
            assert cleaned_value == "__true__"

    def test_not_truthy(self):
        field = form_fields.BooleanField(required=False)
        # Any other string that is NOT in form_fields.BooleanField.truthy_strings
        # should return `!__true__`
        cleaned_value = field.clean("FALSE")
        assert cleaned_value == "!__true__"
        cleaned_value = field.clean("anything")
        assert cleaned_value == "!__true__"
        # But not choke on non-ascii strings
        cleaned_value = field.clean("Nöö")
        assert cleaned_value == "!__true__"

    def test_null(self):
        field = form_fields.BooleanField()
        cleaned_value = field.clean("__null__")
        assert cleaned_value == "__null__"

    def test_not_null(self):
        field = form_fields.BooleanField()
        cleaned_value = field.clean("!__null__")
        assert cleaned_value == "!__null__"
