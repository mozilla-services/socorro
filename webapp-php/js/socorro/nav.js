/*jslint browser:true, regexp:false */ 
/*global window, $*/
$(document).ready(function () {
    var base_url,
        product_version,
        url,
        report;
    $("#q").focus(function () {
        $(this).attr('value', '');
    });
    
    // Used to handle the selection of a specific version of a specific product.
    if ($("#product_version")) {
        $("#product_version").change(function () {
            base_url = $("#base_url").val();
            product_version = $("#product_version").val();
            if (product_version !== 'More Versions') {
                url = base_url + '/versions/' + product_version;
                window.location = url;
            }
        });
    }
    
    // Used to handle the selection of a specific report.
    if ($("#report")) {
        $("#report").change(function () {
            report = $("#report").val();
            if (report !== 'More Reports') {
                window.location = report;
            }
        });
    }
    
});