# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from pathlib import Path
from urllib.parse import quote

from django import http
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import reverse
from django.views.decorators.http import require_GET

from csp.decorators import csp_update

from crashstats import productlib
from crashstats.crashstats import forms, models, utils
from crashstats.crashstats.decorators import track_view, pass_default_context
from crashstats.supersearch.models import SuperSearchFields
from socorro.external.crashstorage_base import CrashIDNotFound


def ratelimit_blocked(request, exception):
    # http://tools.ietf.org/html/rfc6585#page-3
    status = 429

    # NOTE(willkg): this may not work if we switch JS frameworks
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # If the request is an AJAX on, we return a plain short string.
    # Also, if the request is coming from something like curl, it will
    # send the header `Accept: */*`. But if you take the same URL and open
    # it in the browser it'll look something like:
    # `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
    if is_ajax or not request.accepts("text/html"):
        # Return a super spartan message.
        # We could also do something like `{"error": "Too Many Requests"}`
        return http.HttpResponse(
            "Too Many Requests", status=status, content_type="text/plain"
        )

    return render(request, "crashstats/ratelimit_blocked.html", status=status)


def robots_txt(request):
    return http.HttpResponse(
        "User-agent: *\n" "%s: /" % ("Allow" if settings.ENGAGE_ROBOTS else "Disallow"),
        content_type="text/plain",
    )


@require_GET
def contribute_json(request):
    """Serve contribute.json file"""
    index_path = Path(settings.SOCORRO_ROOT) / "contribute.json"
    fp = index_path.open("rb")
    return FileResponse(fp)


@require_GET
def favicon_ico(request):
    """Serve the favicon.ico file"""
    index_path = Path(settings.ROOT) / "crashstats/crashstats/static/img/favicon.ico"
    fp = index_path.open("rb")
    return FileResponse(fp)


def build_id_to_date(build_id):
    yyyymmdd = str(build_id)[:8]
    return "{}-{}-{}".format(yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:8])


@track_view
@csp_update(CONNECT_SRC="analysis-output.telemetry.mozilla.org")
@pass_default_context
def report_index(request, crash_id, default_context=None):
    valid_crash_id = utils.find_crash_id(crash_id)
    if not valid_crash_id:
        return http.HttpResponseBadRequest("Invalid crash ID")

    # Sometimes, in Socorro we use a prefix on the crash ID. Usually it's
    # 'bp-' but this is configurable.
    # If you try to use this to reach the perma link for a crash, it should
    # redirect to the report index with the correct crash ID.
    if valid_crash_id != crash_id:
        return redirect(reverse("crashstats:report_index", args=(valid_crash_id,)))

    context = default_context or {}
    context["crash_id"] = crash_id

    refresh_cache = request.GET.get("refresh") == "cache"

    raw_api = models.RawCrash()
    try:
        context["raw"] = raw_api.get(crash_id=crash_id, refresh_cache=refresh_cache)
    except CrashIDNotFound:
        # If the raw crash can't be found, we can't do much.
        return render(
            request, "crashstats/report_index_not_found.html", context, status=404
        )
    utils.enhance_raw(context["raw"])

    api = models.UnredactedCrash()
    try:
        context["report"] = api.get(crash_id=crash_id, refresh_cache=refresh_cache)
    except CrashIDNotFound:
        # ...if we haven't already done so.
        cache_key = f"priority_job:{crash_id}"
        if not cache.get(cache_key):
            priority_api = models.PriorityJob()
            priority_api.post(crash_ids=[crash_id])
            cache.set(cache_key, True, 60)
        return render(request, "crashstats/report_index_pending.html", context)

    context["product_details"] = productlib.get_product_by_name(
        context["report"]["product"]
    )

    # For C++/Rust crashes
    if "json_dump" in context["report"]:
        json_dump = context["report"]["json_dump"]
        if "sensitive" in json_dump and not request.user.has_perm(
            "crashstats.view_pii"
        ):
            del json_dump["sensitive"]
        context["raw_stackwalker_output"] = json.dumps(
            json_dump, sort_keys=True, indent=4, separators=(",", ": ")
        )
        utils.enhance_json_dump(json_dump, settings.VCS_MAPPINGS)
        parsed_dump = json_dump
    else:
        context["raw_stackwalker_output"] = ""
        parsed_dump = {}

    context["crashing_thread"] = parsed_dump.get("crash_info", {}).get(
        "crashing_thread"
    )
    if context["report"]["signature"].startswith("shutdownhang"):
        # For shutdownhang signatures, we want to use thread 0 as the
        # crashing thread, because that's the thread that actually contains
        # the useful data about what happened.
        context["crashing_thread"] = 0

    context["parsed_dump"] = parsed_dump

    # For Java crashes
    if "java_exception" in context["report"]:
        if request.user.has_perm("crashstats.view_pii"):
            context["java_exception_stacks"] = context["report"]["java_exception_raw"][
                "exception"
            ]["values"]
        else:
            context["java_exception_stacks"] = context["report"]["java_exception"][
                "exception"
            ]["values"]

    context["bug_associations"] = list(
        models.BugAssociation.objects.filter(signature=context["report"]["signature"])
        .values("bug_id", "signature")
        .order_by("-bug_id")
    )

    context["report"]["addons"] = utils.enhance_addons(
        context["raw"], context["report"]
    )

    # Fix processed_crash.mac_crash_info so it displays better
    if "mac_crash_info" in context["report"]:
        mac_crash_info = context["report"]["mac_crash_info"]
        mac_crash_info = json.dumps(
            json.loads(mac_crash_info), indent=2, sort_keys=True
        )
        context["report"]["mac_crash_info"] = mac_crash_info

    context["public_raw_keys"] = [
        x for x in context["raw"] if x in models.RawCrash.API_ALLOWLIST()
    ]
    if request.user.has_perm("crashstats.view_pii"):
        # If the user can see PII or this is their crash report, include everything
        context["protected_raw_keys"] = [
            x for x in context["raw"] if x not in models.RawCrash.API_ALLOWLIST()
        ]
    else:
        context["protected_raw_keys"] = []

    # Sort keys case-insensitively
    context["public_raw_keys"].sort(key=lambda s: s.lower())
    context["protected_raw_keys"].sort(key=lambda s: s.lower())

    data_urls = []
    if request.user.has_perm("crashstats.view_pii"):
        # Add Raw Crash link
        data_urls.append(
            (
                "crash annotations",
                "%s?crash_id=%s"
                % (
                    reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                    crash_id,
                ),
            )
        )

        # Add Processed Crash link
        data_urls.append(
            (
                "processed crash",
                "%s?crash_id=%s"
                % (
                    reverse(
                        "api:model_wrapper", kwargs={"model_name": "UnredactedCrash"}
                    ),
                    crash_id,
                ),
            )
        )
    context["raw_data_urls"] = data_urls

    dump_urls = []
    if request.user.has_perm("crashstats.view_rawdump"):
        # Add link for minidumps and memory report
        dumps = sorted(context["raw"].get("dump_checksums", {}).keys())
        for dump_name in dumps:
            dump_urls.append(
                (
                    dump_name,
                    "%s?crash_id=%s&format=raw&name=%s"
                    % (
                        reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                        crash_id,
                        dump_name,
                    ),
                )
            )
    context["raw_dump_urls"] = dump_urls

    # Add descriptions to all fields.
    all_fields = SuperSearchFields().get()
    descriptions = {}
    for field in all_fields.values():
        key = "{}.{}".format(field["namespace"], field["in_database_name"])
        descriptions[key] = "{} Search: {}".format(
            field.get("description", "").strip() or "No description for this field.",
            field["is_exposed"] and field["name"] or "N/A",
        )

    def make_raw_crash_key(key):
        """In the report_index.html template we need to create a key
        that we can use to look up against the 'fields_desc' dict.
        Because you can't do something like this in jinja::

            {{ fields_desc.get(u'raw_crash.{}'.format(key), empty_desc) }}

        we do it here in the function instead.
        The trick is that the lookup key has to be a unicode object or
        else you get UnicodeEncodeErrors in the template rendering.
        """
        return f"raw_crash.{key}"

    context["make_raw_crash_key"] = make_raw_crash_key
    context["fields_desc"] = descriptions
    context["empty_desc"] = "No description for this field. Search: unknown"

    content = loader.render_to_string("crashstats/report_index.html", context, request)
    utf8_content = content.encode("utf-8", errors="backslashreplace")
    return HttpResponse(utf8_content, charset="utf-8")


@pass_default_context
def login(request, default_context=None):
    context = default_context or {}
    return render(request, "crashstats/login.html", context)


@track_view
def quick_search(request):
    query = request.GET.get("query", "").strip()
    crash_id = utils.find_crash_id(query)

    if crash_id:
        url = reverse("crashstats:report_index", kwargs=dict(crash_id=crash_id))
    elif query:
        url = "%s?signature=%s" % (reverse("supersearch:search"), quote("~%s" % query))
    else:
        url = reverse("supersearch:search")

    return redirect(url)


@utils.json_view
def buginfo(request, signatures=None):
    form = forms.BugInfoForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    bug_ids = form.cleaned_data["bug_ids"]

    bzapi = models.BugzillaBugInfo()
    result = bzapi.get(bug_ids)
    return result


@pass_default_context
def about_throttling(request, default_context=None):
    """Return a simple page that explains about how throttling works."""
    context = default_context or {}
    return render(request, "crashstats/about_throttling.html", context)


@track_view
@pass_default_context
def home(request, default_context=None):
    context = default_context or {}
    return render(request, "crashstats/home.html", context)


@track_view
@pass_default_context
def product_home(request, product, default_context=None):
    context = default_context or {}

    # Figure out versions
    if product in context["active_versions"]:
        context["versions"] = [
            x["version"]
            for x in context["active_versions"][product]
            if x["is_featured"]
        ]
        # If there are no featured versions but there are active
        # versions, then fall back to use that instead.
        if not context["versions"] and context["active_versions"][product]:
            # But when we do that, we have to make a manual cut-off of
            # the number of versions to return. So make it max 4.
            context["versions"] = [
                x["version"] for x in context["active_versions"][product]
            ][: settings.NUMBER_OF_FEATURED_VERSIONS]
    else:
        context["versions"] = []

    return render(request, "crashstats/product_home.html", context)


def handler500(request, template_name="500.html"):
    if getattr(request, "_json_view", False):
        # Every view with the `utils.json_view` decorator sets,
        # on the request object, that it wants to eventually return
        # a JSON output. Let's re-use that fact here.
        return http.JsonResponse(
            {
                "error": "Internal Server Error",
                "path": request.path,
                "query_string": request.META.get("QUERY_STRING"),
            },
            status=500,
        )
    context = {}
    return render(request, "500.html", context, status=500)


def handler404(request, exception, template_name="404.html"):
    if getattr(request, "_json_view", False):
        # Every view with the `utils.json_view` decorator sets,
        # on the request object, that it wants to eventually return
        # a JSON output. Let's re-use that fact here.
        return http.JsonResponse(
            {
                "error": "Page not found",
                "path": request.path,
                "query_string": request.META.get("QUERY_STRING"),
            },
            status=404,
        )
    context = {}
    return render(request, "404.html", context, status=404)
