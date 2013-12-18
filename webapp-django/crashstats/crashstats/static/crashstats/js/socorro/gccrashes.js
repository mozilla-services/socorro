/*global socorro:false, $:false */

$(function() {
    'use strict';
    var supportedProducts = ['Firefox'];
    var selectedProduct = $('#product');

    selectedProduct.on('change', function() {
        var product = $(this).val();

        if ($.inArray(product, supportedProducts) === -1) {
            var response = {
                status: 'error',
                message: 'Report currently only supports ' + supportedProducts.toString()
            };
            socorro.ui.setUserMsg('#gccrashes', response);
        } else {
            // Ensure there are no user message that linger when
            // a supported product is selected.
            socorro.ui.removeUserMsg('#gccrashes');
        }
    });
});
