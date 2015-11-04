$(document).ready(function () {
    var reportsURLs = {};
    $('#report_select option').each(function(i, elem) {
        reportsURLs[elem.value] = {
            'product': elem.dataset.urlProduct,
            'version': elem.dataset.urlVersion,
        };
    });

    var getURL = function () {
        var report = $('#report_select').val();
        var product = $('#products_select').val();
        var version = $('#product_version_select').val();

        var url;

        if (version === 'Current Versions') {
            // That means there is no version set, so we only set the product.
            url = reportsURLs[report].product.replace('__PRODUCT__', product);
        }
        else {
            // There are both a product and a version.
            url = reportsURLs[report].version.replace('__PRODUCT__', product).replace('__VERSION__', version);
        }

        return url;
    };

    $('.version-nav').on('change', 'select', function () {
        window.location = getURL();
    });
});
