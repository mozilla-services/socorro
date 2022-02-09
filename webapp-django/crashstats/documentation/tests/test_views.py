# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from markus.testing import MetricsMock

from django.urls import reverse
from django.utils.encoding import smart_str


def test_home_metrics(client, db):
    url = reverse("documentation:home")
    with MetricsMock() as metrics_mock:
        resp = client.get(url)
    assert resp.status_code == 200
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/",
            "status:200",
        ],
    )


def test_supersearch_home(client, db):
    url = reverse("documentation:supersearch_home")
    with MetricsMock() as metrics_mock:
        response = client.get(url)
    assert response.status_code == 200
    assert "What is Super Search?" in smart_str(response.content)
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/supersearch/",
            "status:200",
        ],
    )


def test_whatsnew(client, db):
    url = reverse("documentation:whatsnew")
    with MetricsMock() as metrics_mock:
        response = client.get(url)
    assert response.status_code == 200
    assert "What's New in Crash Stats" in smart_str(response.content)
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/whatsnew/",
            "status:200",
        ],
    )


def test_supersearch_examples(client, db):
    url = reverse("documentation:supersearch_examples")
    with MetricsMock() as metrics_mock:
        response = client.get(url)
    assert response.status_code == 200
    assert "Examples" in smart_str(response.content)
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/supersearch/examples/",
            "status:200",
        ],
    )


def test_supersearch_api(client, db):
    url = reverse("documentation:supersearch_api")
    with MetricsMock() as metrics_mock:
        response = client.get(url)
    assert response.status_code == 200
    assert "_results_number" in smart_str(response.content)
    assert "_aggs.*" in smart_str(response.content)
    assert "signature" in smart_str(response.content)
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/supersearch/api/",
            "status:200",
        ],
    )


def test_memory_dump_access_redirect(client, db):
    """Verify memory_dump_access url redirects

    This is the old url to the data access policy. In order to keep those links
    working, we need it to redirect to the new url.

    """
    response = client.get("/documentation/memory_dump_access/")
    assert response.status_code == 302
    assert response.url == reverse("documentation:protected_data_access")


def test_signup_renders(client, db):
    url = reverse("documentation:signup")
    with MetricsMock() as metrics_mock:
        response = client.get(url)
    assert response.status_code == 200
    metrics_mock.assert_timing(
        "webapp.view.pageview",
        tags=[
            "ajax:false",
            "api:false",
            "path:/documentation/signup/",
            "status:200",
        ],
    )
