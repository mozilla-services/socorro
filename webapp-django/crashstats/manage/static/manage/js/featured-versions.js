/*global alert:true */
(function ($, document) {
    'use strict';

    function submitForm() {
        // check that every product has at least one featured version
        var no_empty = true;
        $('.product').each(function() {
            if ($('input[type="checkbox"]', this).length && !$('input[type="checkbox"]:checked', this).length) {
                var product = $('h4', this).text();
                no_empty = false;
                alert('No versions selected for ' + product);
            }
        });
        return no_empty;
    }

    $(document).ready(function() {

        // hijack form submissions
        $('form.products').submit(function() {
            return submitForm($(this));
        });

    });

}($, document));
