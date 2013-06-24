$(document).ready(function () {
    var product,
        product_version,
        report;

    // Used to handle the selection of specific product.
    if ($("#products_select")) {
        $("#products_select").change(function () {
            product = $("#products_select").val();
            window.location = '/home/products/' + product;
        });
    }

    // Used to handle the selection of a specific version of a specific product.
    if ($("#product_version_select")) {
        $("#product_version_select").change(function () {
            product_version = $("#product_version_select").val();
            report = $("#report_select").val();
            product = $("#products_select").val();
            if (product_version === 'Current Versions') {
                window.location = report;
            } else if (report.indexOf('/daily') === 0) {
                // FIXME interferes with this report's built-in multi-select
                window.location = '/home/products/' + product +
                                  '/versions/' + product_version;
            } else {
                window.location = report + '/versions/' + product_version;
            }
        });
    }

    // Used to handle the selection of a specific report.
    if ($("#report_select")) {
        $("#report_select").change(function () {
            product_version = $("#product_version_select").val();
            report = $("#report_select").val();
            product = $("#products_select").val();
            if (product_version === 'Current Versions') {
                window.location = report;
            } else if (report.indexOf('/daily') === 0) {
                // FIXME this report uses a different URL structure
                window.location =  report + '&v=' + product_version;
            } else {
                window.location = report + '/versions/' + product_version;
            }
        });
    }
});
