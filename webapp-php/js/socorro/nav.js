
$(document).ready(function(){
    $("#q").focus(function(){
        $(this).attr('value', '');
    });
    
    // Used to handle the selection of a specific version of a specific product.
    if ($("#product_version")) {
        $("#product_version").change(function(){
            var base_url = $("#base_url").val();
            var product_version = $("#product_version").val();
            if (product_version != 'More Versions') {
                var url = base_url + '/versions/' + product_version;
                window.location = url;
            }
        });
    }
    
    // Used to handle the selection of a specific report.
    if ($("#report")) {
        $("#report").change(function(){
            var report = $("#report").val();
            if (report != 'More Reports') {
                window.location = report;
            }
        });
    }
    
});
