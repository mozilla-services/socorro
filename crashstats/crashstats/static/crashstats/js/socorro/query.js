/**
 * Depends on:
 * * PRODUCTS_VERSIONS_MAP - Dictionary of all products, each element being a
 *                           list of all versions of that product.
 * * SEARCH_FORM_PARAMS - Current values of the search parameters, to show and
 *                        select the right versions in the form.
 */
(function ($, window) {
    'use strict';
    var productsVersionsMap = window.PRODUCTS_VERSIONS_MAP,
        searchFormParams = window.SEARCH_FORM_PARAMS,
        dateFormat = 'mm/dd/yyyy hh:mm:ss',
        forceAdvanced = window.location.hash === '#advanced';

    function updateVersions(products, selected) {
        var sel = selected || [],
            featured = [],
            standard = [],
            missingProducts = [],
            featuredOptions,
            standardOptions,
            errorText = 'No version information found for ',
            noVersionFound;

        $.each(products, function (j, product) {
            if (productsVersionsMap[product]) {
                $.each(productsVersionsMap[product], function (i, versions) {
                    var v = [versions.product, versions.version],
                        option = $('<option>').val(v.join(':'))
                                              .text(v.join(' '));

                    if ($.inArray(v.join(':'), sel) >= 0) {
                        option.attr('selected', 'selected');
                    }
                    if (versions.featured) {
                        option.addClass('featured');
                        featured.push(option);
                    } else {
                        standard.push(option);
                    }
                });
            } else {
                missingProducts.push(product);
            }
        });

        if (missingProducts.length === 0) {
            featuredOptions = $("#version optgroup:first").empty();
            standardOptions = $("#version optgroup:last-child").empty();

            $.each(featured, function (i, option) {
                featuredOptions.append(option);
            });
            $.each(standard, function (i, option) {
                standardOptions.append(option);
            });

            $("#no_version_info").remove();
        } else {
            errorText += missingProducts.join(', ');
            noVersionFound = $('<p>').attr('id', 'no_version_info')
                                         .text(errorText);
            $("#searchform").find("fieldset").append(noVersionFound);
        }

        // If nothing was already selected, pick the first item
        if (!$('select[name=version]').val()) {
            $('select[name=version] option:first').attr('selected', 'selected');
        }
    }

    $(document).ready(function () {
        var showAdvFilter = $.cookies.get('advfilter');

        function setAdvancedFiltersCookie(showAdvFilter) {
            $.cookies.set('advfilter', showAdvFilter, {});
        }

        // Advanced filters show or hide
        // If the advanced hash is set in the URL, force showing the
        // advanced filters.
        if (showAdvFilter === null) {
            showAdvFilter = forceAdvanced;
            setAdvancedFiltersCookie(showAdvFilter);
        } else if (!showAdvFilter && forceAdvanced) {
            showAdvFilter = true;
            setAdvancedFiltersCookie(showAdvFilter);
        }

        if (showAdvFilter) {
            $('#advfilter').show();
        } else {
            $('#advfilter').hide();
        }

        $('#advfiltertoggle').click(function () {
            var showAdvFilter = !$.cookies.get('advfilter');
            setAdvancedFiltersCookie(showAdvFilter);

            if (showAdvFilter) {
                $('#advfilter').show('fast');
            } else {
                $('#advfilter').hide('fast');
            }
        });

        //Process/Plugin area
        $('[name=plugin_field]').cookieBind();
        $('[name=plugin_query_type]').cookieBind();

        $('[name=process_type]').bind('change', function () {
            if ($('[name=process_type]:checked').val() === 'plugin') {
                $('#plugin-inputs').removeClass('disabled');
                $('#plugin-inputs *').attr('disabled', null);
            } else {
                $('#plugin-inputs').addClass('disabled');
                $('#plugin-inputs *').attr('disabled', 'disabled');
            }
        }).trigger('change');

        // Results table sorting
        $('#dateHelp *').tooltip();
        $('#signatureList').tablesorter();

        // Upon submitting the form, hide the submit button and disable the
        // refresh options.
        $('#searchform').bind('submit', function () {
            if ($('input[name=date]').val() === dateFormat) {
                $('input[name=date]').val('');
            }

            $('input[type=submit]', this).attr('disabled', 'disabled');
            $('#query_submit').hide();
            $('#query_waiting').show();

            $(document).bind("keypress", function (e) {
                if (e.keyCode === 13 || e.keyCode === 116) {
                    return false;
                }
            });
        });

        // Default value for the date field
        if ($.trim($('input[name=date]').val()) === '') {
            $('input[name=date]').val(dateFormat);
        }

        $('select[name=product]').bind('change', function () {
            var selected =  $('select[name=product]').val();
            if (selected.length > 0) {
                updateVersions(selected);
            }
        });

        updateVersions(searchFormParams.products, searchFormParams.versions);
    });
}($, window));
