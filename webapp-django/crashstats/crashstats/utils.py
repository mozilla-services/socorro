# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import OrderedDict
import datetime
import functools
import isodate
import json
import logging
import random
import re
from urllib.parse import urlencode

import requests

from django import http
from django.conf import settings
from django.core.cache import cache
from django.template import engines
from django.utils import timezone
from django.utils.functional import cached_property

from crashstats.crashstats import models
import crashstats.supersearch.models as supersearch_models
from socorro.lib.versionutil import generate_semver, VersionParseError


logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


def parse_isodate(ds):
    """Return a datetime object from a date string"""
    return isodate.parse_datetime(ds)


def render_exception(exception):
    """When we need to render an exception as HTML.

    Often used to supply as the response body when there's a
    HttpResponseBadRequest.
    """
    template = engines["backend"].from_string("<ul><li>{{ exception }}</li></ul>")
    return template.render({"exception": exception})


def urlencode_obj(thing):
    """Return a URL encoded string, created from a regular dict or any object
    that has a `urlencode` method.

    This function ensures white spaces are encoded with '%20' and not '+'.
    """
    if hasattr(thing, "urlencode"):
        res = thing.urlencode()
    else:
        res = urlencode(thing, True)
    return res.replace("+", "%20")


class SignatureStats:
    def __init__(
        self,
        signature,
        num_total_crashes,
        rank=0,
        platforms=None,
        previous_signature=None,
    ):
        self.signature = signature
        self.num_total_crashes = num_total_crashes
        self.rank = rank
        self.platforms = platforms
        self.previous_signature = previous_signature

    @cached_property
    def platform_codes(self):
        return [x["short_name"] for x in self.platforms if x["short_name"] != "unknown"]

    @cached_property
    def signature_term(self):
        return self.signature["term"]

    @cached_property
    def percent_of_total_crashes(self):
        return 100.0 * self.signature["count"] / self.num_total_crashes

    @cached_property
    def num_crashes(self):
        return self.signature["count"]

    @cached_property
    def num_crashes_per_platform(self):
        num_crashes_per_platform = {
            platform + "_count": 0 for platform in self.platform_codes
        }
        for platform in self.signature["facets"]["platform"]:
            code = platform["term"][:3].lower()
            if code in self.platform_codes:
                num_crashes_per_platform[code + "_count"] = platform["count"]
        return num_crashes_per_platform

    @cached_property
    def num_crashes_in_garbage_collection(self):
        num_crashes_in_garbage_collection = 0
        for row in self.signature["facets"]["is_garbage_collecting"]:
            if row["term"].lower() == "t":
                num_crashes_in_garbage_collection = row["count"]
        return num_crashes_in_garbage_collection

    @cached_property
    def num_installs(self):
        return self.signature["facets"]["cardinality_install_time"]["value"]

    @cached_property
    def percent_of_total_crashes_diff(self):
        if self.previous_signature:
            return (
                self.previous_signature.percent_of_total_crashes
                - self.percent_of_total_crashes
            )
        return "new"

    @cached_property
    def rank_diff(self):
        if self.previous_signature:
            return self.previous_signature.rank - self.rank
        return 0

    @cached_property
    def previous_percent_of_total_crashes(self):
        if self.previous_signature:
            return self.previous_signature.percent_of_total_crashes
        return 0

    @cached_property
    def num_startup_crashes(self):
        return sum(
            row["count"]
            for row in self.signature["facets"]["startup_crash"]
            if row["term"] in ("T", "1")
        )

    @cached_property
    def is_startup_crash(self):
        return self.num_startup_crashes == self.num_crashes

    @cached_property
    def is_potential_startup_crash(self):
        return (
            self.num_startup_crashes > 0 and self.num_startup_crashes < self.num_crashes
        )

    @cached_property
    def is_startup_window_crash(self):
        is_startup_window_crash = False
        for row in self.signature["facets"]["histogram_uptime"]:
            # Aggregation buckets use the lowest value of the bucket as
            # term. So for everything between 0 and 60 excluded, the
            # term will be `0`.
            if row["term"] < 60:
                ratio = 1.0 * row["count"] / self.num_crashes
                is_startup_window_crash = ratio > 0.5
        return is_startup_window_crash

    @cached_property
    def is_hang_crash(self):
        num_hang_crashes = 0
        for row in self.signature["facets"]["hang_type"]:
            # Hangs have weird values in the database: a value of 1 or -1
            # means it is a hang, a value of 0 or missing means it is not.
            if row["term"] in (1, -1):
                num_hang_crashes += row["count"]
        return num_hang_crashes > 0

    @cached_property
    def is_plugin_crash(self):
        for row in self.signature["facets"]["process_type"]:
            if row["term"].lower() == "plugin":
                return row["count"] > 0
        return False

    @cached_property
    def is_startup_related_crash(self):
        return (
            self.is_startup_crash
            or self.is_potential_startup_crash
            or self.is_startup_window_crash
        )


def get_comparison_signatures(results):
    comparison_signatures = {}
    for index, signature in enumerate(results["facets"]["signature"]):
        signature_stats = SignatureStats(
            signature=signature,
            rank=index,
            num_total_crashes=results["total"],
            platforms=None,
            previous_signature=None,
        )
        comparison_signatures[signature_stats.signature_term] = signature_stats
    return comparison_signatures


def json_view(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        request._json_view = True
        response = f(request, *args, **kw)

        if isinstance(response, http.HttpResponse):
            return response

        else:
            indent = 0
            request_data = request.method == "GET" and request.GET or request.POST
            if request_data.get("pretty") == "print":
                indent = 2
            if isinstance(response, tuple) and isinstance(response[1], int):
                response, status = response
            else:
                status = 200
            if isinstance(response, tuple) and isinstance(response[1], dict):
                response, headers = response
            else:
                headers = {}
            http_response = http.HttpResponse(
                _json_clean(json.dumps(response, cls=DateTimeEncoder, indent=indent)),
                status=status,
                content_type="application/json; charset=UTF-8",
            )
            for key, value in headers.items():
                http_response[key] = value
            return http_response

    return wrapper


def _json_clean(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashe\
    # s-escaped
    return value.replace("</", "<\\/")


def enhance_frame(frame, vcs_mappings):
    """
    Add some additional info to a stack frame--signature
    and source links from vcs_mappings.
    """
    if "function" in frame:
        # Remove spaces before all stars, ampersands, and commas
        function = re.sub(r" (?=[\*&,])", "", frame["function"])
        # Ensure a space after commas
        function = re.sub(r",(?! )", ", ", function)
        frame["function"] = function
        signature = function
    elif "file" in frame and "line" in frame:
        signature = "%s#%d" % (frame["file"], frame["line"])
    elif "module" in frame and "module_offset" in frame:
        signature = "%s@%s" % (frame["module"], frame["module_offset"])
    else:
        signature = "@%s" % frame["offset"]
    frame["signature"] = signature
    frame["short_signature"] = re.sub(r"\(.*\)", "", signature)

    if "file" in frame:
        vcsinfo = frame["file"].split(":")
        if len(vcsinfo) == 4:
            vcstype, root, vcs_source_file, revision = vcsinfo
            if "/" in root:
                # The root is something like 'hg.mozilla.org/mozilla-central'
                server, repo = root.split("/", 1)
            else:
                # E.g. 'gecko-generated-sources' or something without a '/'
                repo = server = root

            if (
                vcs_source_file.count("/") > 1
                and len(vcs_source_file.split("/")[0]) == 128
            ):
                # In this case, the 'vcs_source_file' will be something like
                # '{SHA-512 hex}/ipc/ipdl/PCompositorBridgeChild.cpp'
                # So drop the sha part for the sake of the 'file' because
                # we don't want to display a 128 character hex code in the
                # hyperlink text.
                vcs_source_file_display = "/".join(vcs_source_file.split("/")[1:])
            else:
                # Leave it as is if it's not unweildly long.
                vcs_source_file_display = vcs_source_file

            if vcstype in vcs_mappings:
                if server in vcs_mappings[vcstype]:
                    link = vcs_mappings[vcstype][server]
                    frame["file"] = vcs_source_file_display
                    frame["source_link"] = link % {
                        "repo": repo,
                        "file": vcs_source_file,
                        "revision": revision,
                        "line": frame["line"],
                    }
            else:
                path_parts = vcs_source_file.split("/")
                frame["file"] = path_parts.pop()


def enhance_json_dump(dump, vcs_mappings):
    """
    Add some information to the stackwalker's json_dump output
    for display. Mostly applying vcs_mappings to stack frames.
    """
    for i, thread in enumerate(dump.get("threads", [])):
        if "thread" not in thread:
            thread["thread"] = i
        for frame in thread["frames"]:
            enhance_frame(frame, vcs_mappings)
    return dump


def enhance_raw(raw_crash):
    """Enhances raw crash with additional data"""
    if raw_crash.get("AdapterVendorID") and raw_crash.get("AdapterDeviceID"):
        # Look up the two and get friendly names and then add them
        result = models.GraphicsDevice.objects.get_pair(
            raw_crash["AdapterVendorID"], raw_crash["AdapterDeviceID"]
        )
        if result is not None:
            raw_crash["AdapterVendorName"] = result[0]
            raw_crash["AdapterDeviceName"] = result[1]


def get_versions_for_product(product="Firefox", use_cache=True):
    """Returns list of recent version strings for specified product

    This looks at the crash reports submitted for this product over
    VERSIONS_WINDOW_DAYS days and returns the versions of those crash reports.

    If SuperSearch returns an error, this returns an empty list.

    NOTE(willkg): This data is noisy if there are crash reports with junk
    versions.

    :arg str product: the product to query for
    :arg bool use_cache: whether or not to pull results from cache

    :returns: list of versions sorted in reverse order or ``[]``

    """

    if use_cache:
        key = "get_versions_for_product:%s" % product.lower().replace(" ", "")
        ret = cache.get(key)
        if ret is not None:
            return ret

    api = supersearch_models.SuperSearchUnredacted()
    now = timezone.now()

    # Find versions for specified product in crash reports reported in the last
    # VERSIONS_WINDOW_DAYS days and use a big _facets_size so that it picks up versions
    # that have just been released that don't have many crash reports, yet
    window = settings.VERSIONS_WINDOW_DAYS
    params = {
        "product": product,
        "_results_number": 0,
        "_facets": "version",
        "_facets_size": 1000,
        "date": [
            ">=" + (now - datetime.timedelta(days=window)).isoformat(),
            "<" + now.isoformat(),
        ],
    }

    # Since we're caching the results of the search plus additional work done,
    # we don't want to cache the fetch
    ret = api.get(**params, dont_cache=True)
    if "facets" not in ret or "version" not in ret["facets"]:
        return []

    # Get versions from facet, drop junk, and sort the final list
    versions = set()
    for item in ret["facets"]["version"]:
        if item["count"] < settings.VERSIONS_COUNT_THRESHOLD:
            continue

        version = item["term"]

        # Bug #1622932 is about something submitting crash reports with a version of
        # 1024 which is clearly junk, but it messes everything up; this is hacky,
        # but let's just drop those explicitly and push off thinking about a better
        # way of doing all of this until later
        if version.startswith("1024"):
            continue

        try:
            # This generates the sort key but also parses the version to make sure it's
            # a valid looking version
            versions.add((generate_semver(version), version))

            # Add X.Yb to betas set
            if "b" in version:
                beta_version = version[: version.find("b") + 1]
                versions.add((generate_semver(beta_version), beta_version))
        except VersionParseError:
            pass

    # Sort by sortkey and then drop the sortkey
    versions = sorted(versions, key=lambda v: v[0], reverse=True)
    versions = [v[1] for v in versions]

    if use_cache:
        # Cache value for an hour plus a fudge factor in seconds
        cache.set(key, versions, timeout=(60 * 60) + random.randint(60, 120))

    return versions


def get_manually_maintained_featured_versions(product):
    """Returns manually maintained featured versions for a product

    Some products have noisy crash data and so we maintain featured versions in
    a file in the repository. If this file exists, use that set of featured
    versions. Otherwise, we figure it out.

    This looks at GitHub directly rather than look at the local files. This
    allows us to land PRs that update the data and update the featured versions
    on the production site without having to do a production deploy.

    :returns: list of featured versions or None

    """
    url = "%s/%s.json" % (settings.PRODUCT_DETAILS_BASE_URL, product)
    logger.debug("trying %s for featured versions", url)
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()["featured_versions"]
            logger.info("using %s for featured versions", url)
            return data

    except (requests.ConnectionError, json.decoder.JSONDecodeError, KeyError):
        return None


def get_version_context_for_product(product):
    """Returns version context for a specified product

    This gets the versions for a product and generates a context consisting
    of betas, featured versions, and versions.

    If SuperSearch returns an error, this returns an empty list.

    NOTE(willkg): This data can be noisy in cases where crash reports return
    junk versions. We might want to add a "minimum to matter" number.

    :arg product: the product to query for

    :returns: list of version dicts sorted in reverse order or ``[]``

    """
    key = "get_version_context_for_product:%s" % product.lower().replace(" ", "")
    ret = cache.get(key)
    if ret is not None:
        return ret

    versions = get_versions_for_product(product, use_cache=False)

    featured_versions = get_manually_maintained_featured_versions(product)
    if featured_versions is not None:
        # If this product has manually maintained featured versions, use that. Make
        # sure featured versions are in the versions list and re-sort.
        for featured_version in featured_versions:
            if featured_version not in versions:
                versions.insert(0, featured_version)
        versions.sort(key=lambda v: generate_semver(v), reverse=True)

    else:
        # Map of major version (int) -> list of (key (str), versions (str)) so we can
        # get the most recent version of the last three major versions which we'll
        # assume are "featured versions".
        major_to_versions = OrderedDict()
        for version in versions:
            # In figuring for featured versions, we don't want to include the
            # catch-all-betas X.Yb faux version or ESR versions
            if version.endswith(("b", "esr")):
                continue

            try:
                major = int(version.split(".", 1)[0])
                major_to_versions.setdefault(major, []).append(version)
            except ValueError:
                # If the first thing in the major version isn't an int, then skip
                # it
                continue

        # The featured versions is the most recent 3 of the list of recent versions
        # for each major version. Since versions were sorted when we went through
        # them, the most recent one is in index 0.
        featured_versions = [values[0] for values in major_to_versions.values()]
        featured_versions.sort(key=lambda v: generate_semver(v), reverse=True)
        featured_versions = featured_versions[:3]

    # Generate the version data the context needs
    ret = [
        {
            "product": product,
            "version": ver,
            "is_featured": ver in featured_versions,
            "has_builds": False,
        }
        for ver in versions
    ]

    # Cache value for an hour plus a fudge factor in seconds
    cache.set(key, ret, (60 * 60) + random.randint(60, 120))

    return ret


def build_default_context(product=None, versions=None):
    """
    Given a product and a list of versions, generates navbar context.

    Adds ``products`` is a dict of product name -> product information
    for all active supported products.

    Adds ``active_versions`` is a dict of product name -> version information
    for all active supported products.

    Adds ``version`` which is the first version specified from the ``versions``
    argument.

    """
    context = {}

    # Build product information
    context["products"] = list(
        models.Product.objects.active_products().values_list("product_name", flat=True)
    )

    if not product:
        product = settings.DEFAULT_PRODUCT

    if product not in context["products"]:
        raise http.Http404("Not a recognized product")

    context["product"] = product

    # Build product version information for all products
    active_versions = {
        prod: get_version_context_for_product(prod) for prod in context["products"]
    }
    context["active_versions"] = active_versions

    if versions is not None:
        if isinstance(versions, str):
            versions = versions.split(";")

        if versions:
            # Check that versions is a list
            assert isinstance(versions, list)

            # Check that the specified versions are all valid for this product
            pv_versions = [x["version"] for x in active_versions[context["product"]]]
            for version in versions:
                if version not in pv_versions:
                    raise http.Http404("Not a recognized version for that product")

            context["version"] = versions[0]

    return context


_crash_id_regex = re.compile(
    r"^(%s)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{6}[0-9]{6})$" % (settings.CRASH_ID_PREFIX,)
)


def find_crash_id(input_str):
    """Return the valid Crash ID part of a string"""
    for match in _crash_id_regex.findall(input_str):
        try:
            datetime.datetime.strptime(match[1][-6:], "%y%m%d")
            return match[1]
        except ValueError:
            pass  # will return None


def add_CORS_header(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        response = f(request, *args, **kw)
        response["Access-Control-Allow-Origin"] = "*"
        return response

    return wrapper


def ratelimit_rate(group, request):
    """return None if we don't want to set any rate limit.
    Otherwise return a number according to
    https://django-ratelimit.readthedocs.org/en/latest/rates.html#rates-chapter
    """
    if group in (
        "crashstats.api.views.model_wrapper",
        "crashstats.api.views.crash_verify",
    ):
        if request.user.is_active:
            return settings.API_RATE_LIMIT_AUTHENTICATED
        else:
            return settings.API_RATE_LIMIT
    elif group.startswith("crashstats.supersearch.views.search"):
        # this applies to both the web view and ajax views
        if request.user.is_active:
            return settings.RATELIMIT_SUPERSEARCH_AUTHENTICATED
        else:
            return settings.RATELIMIT_SUPERSEARCH
    raise NotImplementedError(group)
