# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


# This determines what files are copied from npm libraries into the
# static root when collectstatic runs.
# The keys are library names (from webapp/package.json) and the
# values are a list of fnmatch patterns to match files to copy.
NPM_FILE_PATTERNS = {
    "jquery-ui": [
        "ui/version.js",
        "ui/widget.js",
        "ui/safe-active-element.js",
        "ui/unique-id.js",
        "ui/keycode.js",
        "ui/widgets/mouse.js",
        "ui/widgets/sortable.js",
        "ui/widgets/datepicker.js",
        "ui/widgets/tabs.js",
    ],
    "Select2": ["select2.js"],
    "metrics-graphics": ["dist/*"],
    "tablesorter": ["dist/js/jquery.tablesorter.js"],
    "d3": ["dist/*"],
    "jssha": ["dist/*.js", "dist/*.map"],
    "qs": ["dist/*"],
    "moment": ["moment.js"],
    "filesize": ["lib/*"],
    "underscore": ["*.js"],
    "jquery.json-viewer": ["json-viewer/jquery.json-viewer.js"],
    "ace-builds": ["src/ace.js", "src/theme-monokai.js", "src/mode-json.js"],
    "jquery": ["dist/*"],
}

PIPELINE_JS = {
    "date_filters": {
        "source_filenames": ("supersearch/js/socorro/date_filters.js",),
        "output_filename": "js/date-filters.min.js",
    },
    "dynamic_form": {
        "source_filenames": ("supersearch/js/lib/dynamic_form.js",),
        "output_filename": "js/dynamic-form.min.js",
    },
    "bugzilla": {
        "source_filenames": ("crashstats/js/socorro/bugzilla.js",),
        "output_filename": "js/bugzilla.min.js",
    },
    "d3": {"source_filenames": ("d3/dist/d3.js",), "output_filename": "js/d3.min.js"},
    "jquery_ui": {
        "source_filenames": (
            "jquery-ui/ui/version.js",
            "jquery-ui/ui/widget.js",
            "jquery-ui/ui/safe-active-element.js",
            "jquery-ui/ui/unique-id.js",
            "jquery-ui/ui/keycode.js",
            "jquery-ui/ui/widgets/mouse.js",
            "jquery-ui/ui/widgets/sortable.js",
            "jquery-ui/ui/widgets/datepicker.js",
            "jquery-ui/ui/widgets/tabs.js",
        ),
        "output_filename": "js/jquery-ui.min.js",
    },
    "accordion": {
        "source_filenames": ("crashstats/js/lib/accordions.js",),
        "output_filename": "js/accordion.min.js",
    },
    "correlation": {
        "source_filenames": (
            "jssha/dist/sha1.js",
            "crashstats/js/socorro/correlation.js",
        ),
        "output_filename": "js/correlation.min.js",
    },
    "metricsgraphics": {
        "source_filenames": ("metrics-graphics/dist/metricsgraphics.js",),
        "output_filename": "js/metricsgraphics.min.js",
    },
    "select2": {
        "source_filenames": ("Select2/select2.js",),
        "output_filename": "js/select2.min.js",
    },
    "tablesorter": {
        "source_filenames": ("tablesorter/dist/js/jquery.tablesorter.js",),
        "output_filename": "js/jquery-tablesorter.min.js",
    },
    "socorro_utils": {
        "source_filenames": ("crashstats/js/socorro/utils.js",),
        "output_filename": "js/socorro-utils.min.js",
    },
    "topcrashers": {
        "source_filenames": ("topcrashers/js/topcrashers.js",),
        "output_filename": "js/topcrashers.min.js",
    },
    "crashstats_base": {
        "source_filenames": (
            "jquery/dist/jquery.js",
            "crashstats/js/jquery/plugins/jquery.cookies.2.2.0.js",
            "qs/dist/qs.js",
            "moment/moment.js",
            "crashstats/js/socorro/timeutils.js",
            "crashstats/js/socorro/nav.js",
        ),
        "output_filename": "js/crashstats-base.min.js",
    },
    "api_documentation": {
        "source_filenames": ("filesize/lib/filesize.js", "api/js/testdrive.js"),
        "output_filename": "js/api-documentation.min.js",
    },
    "documentation": {
        "source_filenames": ("documentation/js/documentation.js",),
        "output_filename": "js/documentation.min.js",
    },
    "jsonview": {
        "source_filenames": ("jquery.json-viewer/json-viewer/jquery.json-viewer.js",),
        "output_filename": "js/jsonview.min.js",
    },
    "report_index": {
        "source_filenames": (
            "crashstats/js/socorro/report.js",
            "crashstats/js/socorro/reprocessing.js",
        ),
        "output_filename": "js/report-index.min.js",
    },
    "report_pending": {
        "source_filenames": ("crashstats/js/socorro/pending.js",),
        "output_filename": "js/report-pending.min.js",
    },
    "signature_report": {
        "source_filenames": (
            "signature/js/signature_report.js",
            "signature/js/signature_tab.js",
            "signature/js/signature_tab_summary.js",
            "signature/js/signature_tab_graphs.js",
            "signature/js/signature_tab_reports.js",
            "signature/js/signature_tab_aggregations.js",
            "signature/js/signature_tab_comments.js",
            "signature/js/signature_tab_correlations.js",
            "signature/js/signature_tab_bugzilla.js",
            "signature/js/signature_panel.js",
        ),
        "output_filename": "js/signature-report.min.js",
    },
    "search_custom": {
        "source_filenames": (
            "ace-builds/src/ace.js",
            "ace-builds/src/theme-monokai.js",
            "ace-builds/src/mode-json.js",
            "supersearch/js/socorro/search_custom.js",
        ),
        "output_filename": "js/search-custom.min.js",
    },
    "search": {
        "source_filenames": ("supersearch/js/socorro/search.js",),
        "output_filename": "js/search.min.js",
    },
    "tokens": {
        "source_filenames": ("tokens/js/home.js",),
        "output_filename": "js/tokens.min.js",
    },
    "error": {
        "source_filenames": ("js/error.js",),
        "output_filename": "js/error.min.js",
    },
}

# These are quality checks--primarily for developers. It checks that you haven't haven't
# accidentally make a string a tuple with an excess comma, no underscores in the bundle
# name and that the bundle file extension is either .js or .css.
#
# We also check, but only warn, if a file is re-used in a different bundle.  That's
# because you might want to consider not including that file in the bundle and instead
# break it out so it can be re-used on its own.
_used = {}
_trouble = set()
for k, v in PIPELINE_JS.items():
    assert isinstance(k, str), k
    out = v["output_filename"]
    assert isinstance(v["source_filenames"], tuple), v
    assert isinstance(out, str), v
    assert not out.split("/")[-1].startswith("."), k
    assert "_" not in out
    assert out.endswith(".min.css") or out.endswith(".min.js")
    for asset_file in v["source_filenames"]:
        if asset_file in _used:
            # Consider using warnings.warn here instead
            print(
                "{:<52} in {:<20} already in {}".format(
                    asset_file, k, _used[asset_file]
                )
            )
            _trouble.add(asset_file)
        _used[asset_file] = k

for asset_file in _trouble:
    print("REPEATED", asset_file)
    found_in = []
    sets = []
    for k, v in PIPELINE_JS.items():
        if asset_file in v["source_filenames"]:
            found_in.append(k)
            sets.append(set(list(v["source_filenames"])))
    print("FOUND IN", found_in)
    print("ALWAYS TOGETHER WITH", set.intersection(*sets))
    break
