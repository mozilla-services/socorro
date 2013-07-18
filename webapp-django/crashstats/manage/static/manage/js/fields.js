/*global alert:true */
(function ($, document) {
    'use strict';

    function submit_form($form) {
        var name = $.trim($('input[name="name"]', $form).val());
        if (name) {
            $.getJSON($form.attr('action'), {name: name}, function(response) {
                var $container = $('.results');

                $('.product', $container).text(response.product);
                $('.transforms tbody tr', $container).remove();

                $.each(response.transforms, function(key, value) {
                    $('<tr>')
                      .append($('<td>').text(key))
                      .append($('<td>').text(value))
                      .appendTo($('.transforms table tbody', $container));
                });
                $container.show();
            });
        }
        return false;
    }

    $(document).ready(function() {

        // hijack form submissions
        $('form.lookup').submit(function() {
            return submit_form($(this));
        });
    });

}($, document));
