# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import OrderedDict
from collections.abc import Generator, Iterable
from dataclasses import dataclass
import datetime
import functools
import isodate
import json
import logging
import random
import re
from typing import Optional, TypedDict
from urllib.parse import urlencode

from django import http
from django.conf import settings
from django.core.cache import cache
from django.template import engines
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.functional import cached_property

from glom import glom

from crashstats import libproduct
from crashstats.crashstats import models
import crashstats.supersearch.models as supersearch_models
from socorro.lib.libversion import generate_semver, VersionParseError
from socorro.signature.utils import strip_leading_zeros


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
            # The number should go "up" when moving towards 100 and "down" when moving
            # towards 0
            return (
                self.percent_of_total_crashes
                - self.previous_signature.percent_of_total_crashes
            )
        return "new"

    @cached_property
    def rank_diff(self):
        if self.previous_signature:
            # The number should go "up" when moving towards 1 and "down" when moving
            # towards infinity
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
            indent = None
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
            json_data = json.dumps(response, cls=DateTimeEncoder, indent=indent)
            http_response = http.HttpResponse(
                _json_clean(json_data),
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
    """Add additional info to a stack frame

    This adds signature and source links from vcs_mappings.

    """
    # If this is a truncation frame, then we don't need to enhance it in any way
    if frame.get("truncated") is not None:
        return

    if frame.get("function"):
        # Remove spaces before all stars, ampersands, and commas
        function = re.sub(r" (?=[\*&,])", "", frame["function"])
        # Ensure a space after commas
        function = re.sub(r",(?! )", ", ", function)
        frame["function"] = function
        signature = function
    elif frame.get("file") and frame.get("line"):
        signature = "%s#%d" % (frame["file"], frame["line"])
    elif frame.get("module") and frame.get("module_offset"):
        signature = "%s@%s" % (
            frame["module"],
            strip_leading_zeros(frame["module_offset"]),
        )
    elif frame.get("unloaded_modules"):
        first_module = frame["unloaded_modules"][0]
        if first_module.get("offsets"):
            signature = "(unloaded %s@%s)" % (
                first_module.get("module") or "",
                strip_leading_zeros(first_module.get("offsets")[0]),
            )
        else:
            signature = "(unloaded %s)" % first_module
    else:
        signature = "@%s" % frame["offset"]

    frame["signature"] = signature
    if signature.startswith("(unloaded"):
        # If the signature is based on an unloaded module, leave the string as is
        frame["short_signature"] = signature
    else:
        # Remove arguments which are enclosed in parens
        frame["short_signature"] = re.sub(r"\(.*\)", "", signature)

    if frame.get("file"):
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
    for thread_index, thread in enumerate(dump.get("threads", [])):
        if "thread" not in thread:
            thread["thread"] = thread_index

        frames = thread["frames"]
        for frame in frames:
            enhance_frame(frame, vcs_mappings)
            for inline in frame.get("inlines") or []:
                enhance_frame(inline, vcs_mappings)

        thread["frames"] = frames
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


# From /toolkit/mozapps/extensions/AddonManager.jsm Addon.signedState section
# in mozilla-central
SIGNED_STATE_ID_TO_NAME = {
    None: "SIGNEDSTATE_NOT_REQUIRED",
    -2: "SIGNEDSTATE_BROKEN",
    # Add-on may be signed but by an certificate that doesn't chain to our
    # our trusted certificate.
    -1: "SIGNEDSTATE_UNKNOWN",
    # Add-on is unsigned.
    0: "SIGNEDSTATE_MISSING",
    # Add-on is preliminarily reviewed.
    1: "SIGNEDSTATE_PRELIMINARY",
    # Add-on is fully reviewed.
    2: "SIGNEDSTATE_SIGNED",
    # Add-on is system add-on.
    3: "SIGNEDSTATE_SYSTEM",
    # Add-on is signed with a "Mozilla Extensions" certificate
    4: "SIGNEDSTATE_PRIVILEGED",
}


@dataclass
class Addon:
    id: str
    version: str
    name: Optional[str] = None
    is_system: Optional[bool] = None
    signed_state: Optional[int] = None

    def get_signed_state_name(self):
        return SIGNED_STATE_ID_TO_NAME.get(self.signed_state, self.signed_state)


def enhance_addons(raw_crash, processed_crash):
    """Enhances "addons" in processed crash with TelemetryEnvironment information

    :arg raw_crash: the raw crash structure
    :arg processed_crash: the processed crash structure

    :returns: list of Addon instances

    """
    addon_data = processed_crash.get("addons", [])
    if not addon_data:
        return []

    try:
        telemetry_environment = json.loads(raw_crash.get("TelemetryEnvironment", "{}"))
        active_addons = glom(telemetry_environment, "addons.activeAddons", default={})
    except json.JSONDecodeError:
        active_addons = {}

    ret = []
    for addon_line in addon_data:
        split_data = addon_line.split(":")
        extension_id = ""
        version = ""

        if len(split_data) >= 1:
            extension_id = split_data[0]
        if len(split_data) >= 2:
            version = split_data[1]

        addon = Addon(id=extension_id, version=version)

        more_data = active_addons.get(extension_id, {})
        addon.name = more_data.get("name", None)
        addon.is_system = more_data.get("isSystem", None)
        addon.signed_state = more_data.get("signedState", None)

        ret.append(addon)

    return ret


def drop_beta_num(version):
    if "b" in version:
        return version[: version.find("b") + 1]
    return version


def get_versions_for_product(product, use_cache=True):
    """Returns list of recent version strings for specified product

    This looks at the crash reports submitted for this product over
    VERSIONS_WINDOW_DAYS days and returns the versions of those crash reports.

    If SuperSearch returns an error, this returns an empty list.

    NOTE(willkg): This data is noisy if there are crash reports with junk
    versions.

    :arg product: either a product name or Product to query for
    :arg bool use_cache: whether or not to pull results from cache

    :returns: list of versions sorted in reverse order or ``[]``

    """
    if isinstance(product, str):
        product = libproduct.get_product_by_name(product)

    if use_cache:
        key = "get_versions_for_product:%s" % product.name.lower().replace(" ", "")
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
        "product": product.name,
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
                beta_version = drop_beta_num(version)
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


def get_version_json_data(url, use_cache=True):
    """Return data at version json url.

    Results for HTTP 200 responses are cached for an hour.

    :arg url: the url to a json-encoded version file
    :arg use_cache: whether or not to pull results from cache

    :returns: dict

    """
    if not url:
        return {}

    if use_cache:
        key = "get_version_json:%s" % "".join([c for c in url if c.isalnum()])
        ret = cache.get(key)
        if ret is not None:
            return ret

    try:
        data = libproduct.get_version_json_data(url)
    except libproduct.VersionDataError as exc:
        logger.error("fetching %s kicked up error: %s", url, exc)
        data = {}

    if use_cache:
        # Cache value for an hour plus a fudge factor in seconds
        cache.set(key, data, timeout=(60 * 60) + random.randint(60, 120))

    return data


def get_version_context_for_product(product):
    """Returns version context for a specified product

    This gets the versions for a product and generates a context consisting
    of betas, featured versions, and versions.

    If SuperSearch returns an error, this returns an empty list.

    NOTE(willkg): This data can be noisy in cases where crash reports return
    junk versions. We might want to add a "minimum to matter" number.

    :arg product: the Product to query for

    :returns: list of version dicts sorted in reverse order or ``[]``

    """
    key = "get_version_context_for_product:%s" % product.name.lower().replace(" ", "")
    ret = cache.get(key)
    if ret is not None:
        return ret

    versions = get_versions_for_product(product, use_cache=False)

    featured_versions = []
    for item in product.featured_versions:
        if item == "auto":
            # Add automatically determined featured versions based on what crash reports have
            # been collected

            # Map of (major, minor) -> list of (key (str), versions (str)) so we can get the
            # most recent version of the last three major versions which we'll assume are
            # "featured versions".
            major_minor_to_versions = OrderedDict()
            for version in versions:
                # In figuring for featured versions, we don't want to include the
                # catch-all-betas X.Yb faux version or ESR versions
                if version.endswith(("b", "esr")):
                    continue

                try:
                    semver = generate_semver(version)
                    major_minor_key = (semver.major, semver.minor)
                    major_minor_to_versions.setdefault(major_minor_key, []).append(
                        version
                    )
                except VersionParseError:
                    # If this doesn't parse, then skip it
                    continue

            # The featured versions is the most recent 3 of the list of recent versions
            # for each major version. Since versions were sorted when we went through
            # them, the most recent one is in index 0.
            auto_versions = [values[0] for values in major_minor_to_versions.values()]
            auto_versions.sort(key=lambda v: generate_semver(v), reverse=True)
            featured_versions.extend(auto_versions[:3])

        else:
            # See if the item is from version data
            version_json_key, version_path = item.split(".", 2)
            version_json_url = product.version_json_urls.get(version_json_key)
            if version_json_url:
                data = get_version_json_data(version_json_url, use_cache=False)
                if data:
                    version = glom(data, version_path, default="")
                    if version:
                        # Add X.Yb to the set
                        if "b" in version:
                            beta_version = drop_beta_num(version)
                            if beta_version not in featured_versions:
                                featured_versions.append(beta_version)

                        if version not in featured_versions:
                            featured_versions.append(version)

                        continue

            # Add manually added featured versions that aren't already in featured
            # versions
            if item not in featured_versions:
                featured_versions.append(item)

    # Move the featured_version to the beginning of the versions list; this way featured
    # versions are displayed in the order specified in the product details file
    for item in featured_versions:
        if item in versions:
            versions.remove(item)

        versions.insert(0, item)

    # Generate the version data the context needs
    ret = [
        {
            "product": product.name,
            "version": ver,
            "is_featured": ver in featured_versions,
            "has_builds": False,
        }
        for ver in versions
    ]

    # Cache value for an hour plus a fudge factor in seconds
    cache.set(key, ret, (60 * 60) + random.randint(60, 120))

    return ret


def build_default_context(product_name=None, versions=None):
    """
    Given a product name and a list of versions, generates navbar context.

    Adds ``products`` is a dict of product name -> product information
    for all active supported products.

    Adds ``active_versions`` is a dict of product name -> version information
    for all active supported products.

    Adds ``version`` which is the first version specified from the ``versions``
    argument.

    """
    context = {}

    # Build product information
    all_products = libproduct.get_products()
    context["products"] = all_products

    try:
        if not product_name:
            product = libproduct.get_default_product()
        else:
            product = libproduct.get_product_by_name(product_name)
    except libproduct.ProductDoesNotExist as exc:
        raise http.Http404("Not a recognized product") from exc

    context["product"] = product

    # Build product version information for all products
    active_versions = {
        prod.name: get_version_context_for_product(prod) for prod in all_products
    }
    context["active_versions"] = active_versions

    if versions is not None:
        if isinstance(versions, str):
            versions = versions.split(";")

        if versions:
            # Check that versions is a list
            assert isinstance(versions, list)

            # Check that the specified versions are all valid for this product
            pv_versions = [x["version"] for x in active_versions[product.name]]
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


def ratelimit_rate(group, request):
    """Returns supersearch or regular rate limits depending on authentication"""
    if group.startswith("crashstats.supersearch.views.search"):
        # this applies to both the web view and ajax views
        if request.user.is_active:
            return settings.RATELIMIT_SUPERSEARCH_AUTHENTICATED
        else:
            return settings.RATELIMIT_SUPERSEARCH

    if request.user.is_active:
        return settings.API_RATE_LIMIT_AUTHENTICATED
    else:
        return settings.API_RATE_LIMIT


def string_hex_to_hex_string(hexcode):
    """Convert text like 919A to 0x919a

    The PCIDatabase.com uses shortened hex strings (e.g. '919A') whereas in Socorro we
    use the full represenation, but still as a string (e.g. '0x919a').

    When converting the snippet to a 16 base int, we can potentially lose the leading
    zeros, but we want to make sure we always return a 4 character string preceeded by
    0x.

    :arg hexcode: original hex code from pci ids file

    :returns: hexcode in `0xNNNN` format

    """
    return "0x" + format(int(hexcode, 16), "04x")


VENDOR_RE = re.compile(r"^([0-9a-f]{4}) +(.+)$")
DEVICE_RE = re.compile(r"^\t([0-9a-f]{4}) +(.+)$")
SUBDEVICE_RE = re.compile(r"^\t\t([0-9a-f]{4}) ([0-9a-f]{4}) +(.+)$")


class PCIDeviceDesc(TypedDict):
    """Dictionary type yielded by pci_ids__parse_graphics_devices_iterable()."""

    vendor_hex: str
    vendor_name: str
    adapter_hex: str
    adapter_name: str


def pci_ids__parse_graphics_devices_iterable(
    iterable: Iterable[str], debug: bool = False
) -> Generator[PCIDeviceDesc]:
    """
    This function is for parsing the CSVish files from https://pci-ids.ucw.cz/

    :arg iterable: iterable of lines of text
    :arg bool debug: whether or not to print debugging output

    yield dicts that contain the following keys:

    * vendor_hex
    * vendor_name
    * adapter_hex
    * adapter_name

    Rows that start with a `#` are considered comments.

    From the pci.ids file::

        # Syntax:
        # vendor  vendor_name
        #     device  device_name                       <-- single tab indent
        #         subvendor subdevice  subsystem_name   <-- two tab indent

    Since we are only interested in device and vendor ids, we can skip subsystem id lines.

    """
    vendor_hex = vendor_name = None

    for line in iterable:
        line = smart_str(line)

        if not line or line.startswith("#"):
            if "List of known device classes" in line:
                # There's a section at the bottom of the files which
                # we don't need to parse.
                break
            continue

        if match := VENDOR_RE.match(line):
            vendor_hex = string_hex_to_hex_string(match.group(1))
            vendor_name = match.group(2)
        elif match := DEVICE_RE.match(line):
            # vendor_hex and vendor_name must have been set by now. Explicitly asserting this
            # makes the type checker happy.
            assert vendor_hex and vendor_name
            adapter_hex = string_hex_to_hex_string(match.group(1))
            adapter_name = match.group(2)
            yield {
                "vendor_hex": vendor_hex,
                "vendor_name": vendor_name,
                "adapter_hex": adapter_hex,
                "adapter_name": adapter_name,
            }
        elif SUBDEVICE_RE.match(line):
            # We don't currently pretty-print subsystem ids in the web interface, but we may
            # at some point in the future, so we keep this code here. It also helps making the
            # debug output useful – printing tens of thousands of subsystem lines from pci.ids
            # in debug mode would give any useful signal.
            pass
        elif debug:
            print(f"Doesn't match: {line!r}")
