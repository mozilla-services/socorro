/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(document).ready(function () {
    var url_base = $("#url_base").val(),
        url_site = $("#url_site").val(),
        product,
        product_version,
        report;

    $("#q").focus(function () {
        $(this).attr('value', '');
    });

    // Used to handle the selection of specific product.
    if ($("#products_select")) {
        $("#products_select").change(function () {
            product = $("#products_select").val();
            window.location = url_site + 'products/' + product;
        });
    }

    // Used to handle the selection of a specific version of a specific product.
    if ($("#product_version_select")) {
        $("#product_version_select").change(function () {
            product_version = $("#product_version_select").val();
            if (product_version == 'Current Versions') {
                window.location = url_base;
            } else {
                window.location = url_base + '/versions/' + product_version;
            }
        });
    }

    // Used to handle the selection of a specific report.
    if ($("#report_select")) {
        $("#report_select").change(function () {
            report = $("#report_select").val();
            
            // Handle top crasher selection. If no version was selected in the version drop-down
            // select the top most version and append to the URL.
            if(report.indexOf('topcrasher') !== -1) {
                var selectedVersion = $("#product_version_select").val();
                
                if(selectedVersion === "Current Versions") {
                    selectedVersion = $("#product_version_select").find("option:eq(1)").val();
                    window.location = report + selectedVersion;
                } else {
                    window.location = report;
                }
            } else if (report !== 'More Reports') {
                window.location = report;
            }
        });
    }
});
