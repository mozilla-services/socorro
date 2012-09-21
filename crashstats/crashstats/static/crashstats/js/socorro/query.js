$(document).ready(function() {
    var dateFormat = 'mm/dd/yyyy hh:mm:ss',
        queryParams = window.location.search,
        showAdvFilter = $.cookies.get('advfilter');

    function setAdvancedFiltersCookie(showAdvFilter) {
        var showAdvFilterCookieOpts = {};
        $.cookies.set('advfilter', showAdvFilter, showAdvFilterCookieOpts);
    }

    // Advanced filters show or hide
    // If the advanced parameter is set in the URL, force showing the
    // advanced filters.
    if (showAdvFilter === null) {
        if (queryParams.indexOf("advanced=1") > -1) {
            showAdvFilter = true;
        }
        else {
            showAdvFilter = false;
        }
        setAdvancedFiltersCookie(showAdvFilter);
    }
    else if (showAdvFilter === false &&
             queryParams.indexOf("advanced=1") > -1) {
        showAdvFilter = true;
        setAdvancedFiltersCookie(showAdvFilter);
    }

    if (showAdvFilter) {
        $('#advfilter').show();
    }
    else {
        $('#advfilter').hide();
    }

    $('#advfiltertoggle').click(function() {
        var showAdvFilter = ! $.cookies.get('advfilter');
        setAdvancedFiltersCookie(showAdvFilter);

        if (showAdvFilter) {
            $('#advfilter').show("fast");
        }
        else {
            $('#advfilter').hide("fast");
        }
    });

    //Process/Plugin area
    $('[name=plugin_field]').cookieBind();
    $('[name=plugin_query_type]').cookieBind();

    $('[name=process_type]').bind('change', function() {
        if ($('[name=process_type]:checked').val() == "plugin") {
            $('#plugin-inputs').removeClass('disabled');
	        $('#plugin-inputs *').attr('disabled', null);
        }
        else {
	        $('#plugin-inputs').addClass('disabled');
	        $('#plugin-inputs *').attr('disabled', 'disabled');
        }
    }).trigger('change');

    // Results table sorting
    $(function() {
        $('#dateHelp *').tooltip();
        $('#signatureList').tablesorter({
            headers: {
                0: { sorter: 'digit' },
                3: { sorter: 'digit' },
                4: { sorter: 'digit' },
                5: { sorter: 'digit' },
                6: { sorter: 'digit' }
            }
        });
    });

    // Upon submitting the form, hide the submit button and disable the
    // refresh options.
    $('#searchform').bind('submit', function () {
        if ($('input[name=date]').val() == dateFormat) {
            $('input[name=date]').val('');
        }

        $('input[type=submit]', this).attr('disabled', 'disabled');
        $('#query_submit').hide();
        $('#query_waiting').show();

        $(document).bind("keypress", function(e) {
            if (e.keyCode == 13 || e.keyCode == 116) {
                return false;
            }
        });
    });

    if ($.trim($('input[name=date]').val()) == "") {
        $('input[name=date]').val(dateFormat);
    }

    function productUpdater() {
        var selected =  $('select[name=product]').val();
        if (selected.length > 0) {
	       updateVersion(selected);
        }
    }

    $('select[name=product]').bind('change', productUpdater);

    function updateVersion(products, selected) {
        var sel = selected || [],
            product = "",
            featured = "",
            standard = "",
            productInMap;

        for (var j = 0, l = products.length; j < l; j++) {
            product = products[j];
            productInMap = false;
            if (prodVersMap[product] !== undefined) {
                productInMap = true;
                for (var i = 0; i < prodVersMap[product].length; i++) {
                    var v = [prodVersMap[product][i]['product'],
                             prodVersMap[product][i]['version']];
                    var att = "";
                    if ($.inArray(v.join(':'), sel) >= 0) {
                        att = " selected";
                    }
                    if (prodVersMap[product][i]['featured']) {
                        featured += "<option class='featured' value='" + v.join(':') + "'" + att + ">" + v.join(' ') + "</option>";
                    }
                    else {
                        standard += "<option value='" + v.join(':') + "'" + att + ">" + v.join(' ') + "</option>";
                    }
                }
            }
        }
        if (productInMap) {
            $("#no_version_info").remove();
            $("#version optgroup:first").empty().append(featured);
            $("#version optgroup:last-child").empty().append(standard);
        }
        else {
            $("#searchform").find("fieldset").append("<p id='no_version_info'>No version information found for " + product + "</p>");
        }

        //If nothing was already selected, pick the first item
        if ($('select[name=version]').val() == null) {
            $('select[name=version] option:first').attr('selected', true);
        }
    }

    updateVersion(socSearchFormModel.products, socSearchFormModel.versions);

    $('#gofilter').bind('click', function() {
        $('#searchform').submit();
    });
    window.updateVersion = updateVersion;
});
