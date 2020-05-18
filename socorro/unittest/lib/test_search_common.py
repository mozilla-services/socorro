# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import pytest

from socorro.lib import BadArgumentError, datetimeutil
from socorro.lib.search_common import (
    SearchBase,
    SearchParam,
    convert_to_type,
    get_parameters,
    restrict_fields,
)


SUPERSEARCH_FIELDS_MOCKED_RESULTS = {
    "signature": {
        "name": "signature",
        "data_validation_type": "str",
        "query_type": "string",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "product": {
        "name": "product",
        "data_validation_type": "enum",
        "query_type": "enum",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "version": {
        "name": "version",
        "data_validation_type": "str",
        "query_type": "string",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "date": {
        "name": "date",
        "data_validation_type": "datetime",
        "query_type": "date",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "build_id": {
        "name": "build_id",
        "data_validation_type": "int",
        "query_type": "number",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "process_type": {
        "name": "process_type",
        "data_validation_type": "str",
        "query_type": "string",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "hang_type": {
        "name": "hang_type",
        "data_validation_type": "enum",
        "query_type": "enum",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
    "user_comments": {
        "name": "user_comments",
        "data_validation_type": "str",
        "query_type": "string",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "is_exposed": True,
        "is_returned": True,
    },
}


class SearchBaseWithFields(SearchBase):
    def get_parameters(self, **kwargs):
        kwargs["_fields"] = SUPERSEARCH_FIELDS_MOCKED_RESULTS
        return super().get_parameters(**kwargs)


class TestSearchBase:
    def test_get_parameters(self):
        search = SearchBaseWithFields()

        args = {"signature": "mysig", "product": "WaterWolf", "version": "1.0"}
        params = search.get_parameters(**args)
        for i in ("signature", "product", "version"):
            assert i in params
            assert isinstance(params[i], list)
            assert isinstance(params[i][0], SearchParam)
            assert params[i][0].operator == ""

        args = {
            "signature": "~js",
            "product": ["WaterWolf", "NightTrain"],
            "hang_type": "=hang",
        }
        params = search.get_parameters(**args)
        assert params["signature"][0].operator == "~"
        assert params["signature"][0].value == "js"
        assert params["product"][0].operator == ""
        # Test that params with no operator are stacked
        assert params["product"][0].value == ["WaterWolf", "NightTrain"]
        assert params["hang_type"][0].operator == ""

        args = {"signature": ["~Mark", "$js"]}
        params = search.get_parameters(**args)
        assert params["signature"][0].operator == "~"
        assert params["signature"][0].value == "Mark"
        assert params["signature"][1].operator == "$"
        assert params["signature"][1].value == "js"

        args = {"build_id": [">20000101000000", "<20150101000000"]}
        params = search.get_parameters(**args)
        assert params["build_id"][0].operator == ">"
        assert params["build_id"][0].value == 20000101000000
        assert params["build_id"][1].operator == "<"
        assert params["build_id"][1].value == 20150101000000

    def test_get_parameters_with_not(self):
        search = SearchBaseWithFields()

        args = {
            "signature": "!~mysig",
            "product": "!WaterWolf",
            "version": "1.0",
            "user_comments": "!__null__",
        }
        params = search.get_parameters(**args)
        assert params["signature"][0].operator == "~"
        assert params["signature"][0].operator_not
        assert params["signature"][0].value == "mysig"

        assert params["product"][0].operator == ""
        assert params["product"][0].operator_not

        assert params["version"][0].operator == ""
        assert not params["version"][0].operator_not

        assert params["user_comments"][0].operator == "__null__"
        assert params["user_comments"][0].operator_not

    def test_get_parameters_date_no_operator(self):
        search = SearchBaseWithFields()

        # the date parameter must always have a prefix operator
        with pytest.raises(BadArgumentError):
            search.get_parameters(date="2016-01-01")

    def test_get_parameters_date_defaults(self):
        search = SearchBaseWithFields()

        now = datetimeutil.utc_now()

        # Test default values when nothing is passed
        params = search.get_parameters()
        assert "date" in params
        assert len(params["date"]) == 2

        # Pass only the high value
        args = {"date": "<%s" % datetimeutil.date_to_string(now)}
        params = search.get_parameters(**args)
        assert "date" in params
        assert len(params["date"]) == 2
        assert params["date"][0].operator == "<"
        assert params["date"][1].operator == ">="
        assert params["date"][0].value.date() == now.date()
        assert params["date"][1].value.date() == now.date() - datetime.timedelta(days=7)

        # Pass only the low value
        pasttime = now - datetime.timedelta(days=10)
        args = {"date": ">=%s" % datetimeutil.date_to_string(pasttime)}
        params = search.get_parameters(**args)
        assert "date" in params
        assert len(params["date"]) == 2
        assert params["date"][0].operator == "<="
        assert params["date"][1].operator == ">="
        assert params["date"][0].value.date() == now.date()
        assert params["date"][1].value.date() == pasttime.date()

        # Pass the two values
        pasttime = now - datetime.timedelta(days=10)
        args = {
            "date": [
                "<%s" % datetimeutil.date_to_string(now),
                ">%s" % datetimeutil.date_to_string(pasttime),
            ]
        }
        params = search.get_parameters(**args)
        assert "date" in params
        assert len(params["date"]) == 2
        assert params["date"][0].operator == "<"
        assert params["date"][1].operator == ">"
        assert params["date"][0].value.date() == now.date()
        assert params["date"][1].value.date() == pasttime.date()

    def test_get_parameters_date_max_range(self):
        search = SearchBaseWithFields()

        with pytest.raises(BadArgumentError):
            search.get_parameters(date=">1999-01-01")

    def test_process_type_parameter_correction(self):
        search = SearchBaseWithFields()

        args = {"process_type": "browser"}
        params = search.get_parameters(**args)
        assert "process_type" in params
        assert len(params["process_type"]) == 1
        assert params["process_type"][0].value == [""]
        assert params["process_type"][0].operator == "__null__"
        assert params["process_type"][0].operator_not is False

        args = {"process_type": "=browser"}
        params = search.get_parameters(**args)
        assert "process_type" in params
        assert len(params["process_type"]) == 1
        assert params["process_type"][0].value == [""]
        assert params["process_type"][0].operator == "__null__"
        assert params["process_type"][0].operator_not is False

    def test_hang_type_parameter_correction(self):
        search = SearchBaseWithFields()

        args = {"hang_type": "hang"}
        params = search.get_parameters(**args)
        assert "hang_type" in params
        assert len(params["hang_type"]) == 1
        assert params["hang_type"][0].value == [-1, 1]

        args = {"hang_type": "crash"}
        params = search.get_parameters(**args)
        assert "hang_type" in params
        assert len(params["hang_type"]) == 1
        assert params["hang_type"][0].value == [0]

    def test_version_parameter_correction(self):
        search = SearchBaseWithFields()

        args = {"version": ["38.0b"]}
        params = search.get_parameters(**args)
        assert "version" in params
        assert len(params["version"]) == 1
        assert params["version"][0].value == "38.0b"
        assert params["version"][0].operator == "^"
        assert params["version"][0].operator_not is False

        args = {"version": ["1.9b2", "1.9b", "!2.9b", "$.0b"]}
        params = search.get_parameters(**args)
        assert "version" in params
        assert len(params["version"]) == 4
        for param in params["version"]:
            assert param.operator in ("$", "^", "")

            if param.operator == "^" and not param.operator_not:
                # starts with, this one was made up.
                assert param.value == "1.9b"
            elif param.operator == "^" and param.operator_not:
                # starts with, this one was made up.
                assert param.value == "2.9b"
            elif param.operator == "$":
                assert param.value == ".0b"
            elif param.operator == "":
                assert param.value == ["1.9b2"]


class TestSearchCommon:
    """Test functions of the search_common module. """

    def test_convert_to_type(self):
        # Test null
        res = convert_to_type(None, "datetime")
        assert res is None

        # Test integer
        res = convert_to_type(12, "int")
        assert res == 12

        # Test integer
        res = convert_to_type("12", "int")
        assert res == 12

        # Test string
        res = convert_to_type(datetime.datetime(2012, 1, 1), "str")
        assert res == "2012-01-01 00:00:00"

        # Test boolean
        res = convert_to_type(1, "bool")
        assert res is True

        # Test boolean
        res = convert_to_type("T", "bool")
        assert res is True

        # Test boolean
        res = convert_to_type(14, "bool")
        assert res is False

        # Test datetime
        res = convert_to_type("2012-01-01T12:23:34", "datetime")
        assert isinstance(res, datetime.datetime)
        assert res.year == 2012
        assert res.month == 1
        assert res.hour == 12

        # Test date
        res = convert_to_type("2012-01-01T00:00:00", "date")
        assert isinstance(res, datetime.date)
        assert res.year == 2012
        assert res.month == 1

        # Test error
        with pytest.raises(ValueError):
            convert_to_type("abds", "int")
        with pytest.raises(ValueError):
            convert_to_type("2013-02-32", "date")

    def test_get_parameters(self):
        """
        Test search_common.get_parameters()
        """
        # Empty params, only default values are returned
        params = get_parameters({})
        assert params

        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                assert typei is datetime.datetime
            else:
                assert not params[i] or typei in (int, str, list)

        # Empty params
        params = get_parameters(
            {
                "terms": "",
                "fields": "",
                "products": "",
                "from_date": "",
                "to_date": "",
                "versions": "",
                "reasons": "",
                "release_channels": "",
                "os": "",
                "search_mode": "",
                "build_ids": "",
                "report_process": "",
                "report_type": "",
                "plugin_in": "",
                "plugin_search_mode": "",
                "plugin_terms": "",
            }
        )
        assert params, "SearchCommon.get_parameters() returned something empty or null."
        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                assert typei is datetime.datetime
            else:
                assert not params[i] or typei in (int, str, list)

        # Test with encoded slashes in terms and signature
        params = get_parameters(
            {"terms": ["some", "terms/sig"], "signature": "my/little/signature"}
        )

        assert "signature" in params
        assert "terms" in params
        assert params["terms"] == ["some", "terms/sig"]
        assert params["signature"] == "my/little/signature"

    def test_restrict_fields(self):
        """
        Test search_common.restrict_fields()
        """
        authorized_fields = ["signature", "dump"]

        fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump", None, "dump"]
        theoric_fields = ["signature", "dump"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        assert restricted_fields == theoric_fields

        fields = []
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        assert restricted_fields == theoric_fields

        fields = None
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        assert restricted_fields == theoric_fields

        fields = ["nothing"]
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        assert restricted_fields == theoric_fields

        with pytest.raises(ValueError):
            restrict_fields(fields, [])

        with pytest.raises(TypeError):
            restrict_fields(fields, None)
