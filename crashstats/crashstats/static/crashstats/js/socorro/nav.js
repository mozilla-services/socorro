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
            window.location = report;
        });
    }

    // Used to handle the selection of a specific report.
    if ($("#report_select")) {
        $("#report_select").change(function () {
            report = $("#report_select").val();
            window.location = report;
        });
    }
});
