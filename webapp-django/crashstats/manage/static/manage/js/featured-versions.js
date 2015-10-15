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

        if (document.location.host !== 'crash-stats.mozilla.com') {
            // indicate what prod has for its featured versions
            $.getJSON('https://crash-stats.mozilla.com/api/CurrentVersions/')
            .done(function(products) {
                $('.featured-on-prod').show();
                var featured = {};
                $.each(products, function(i, product) {
                    if (product.featured) {
                        if (!featured[product.product]) {
                            featured[product.product] = [];
                        }
                        featured[product.product].push(product.version);
                    }
                });

                $('.featured-on-prod button').on('click', function() {
                    $('input[type="checkbox"]:checked').attr('checked', false);
                    $('tbody tr').each(function() {
                        var product = $('td', this).eq(0).text();
                        var version = $('td', this).eq(1).text();
                        if (featured[product].indexOf(version) > -1) {
                            $('input[type="checkbox"]', this).attr('checked', true);
                        }
                    });
                    $('.featured-on-prod p:hidden').show(600);
                });
            })
            .fail(function() {
                console.error.apply(console, arguments);
            });
        }
    });

}($, document));
