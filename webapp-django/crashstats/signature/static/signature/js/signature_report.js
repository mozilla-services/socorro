/* global socorro:true, $:true */

$(function () {
    'use strict';

    // parameters
    var form = $('#search-form form');
    var fieldsURL = form.data('fields-url');
    var tabsElt = $('.tabs');

    var pageNum = 1;  // the page number as passed in the URL

    var initializedTabs = {};
    var tabsLoadFunctions = {};

    function loadTab(tabName) {
        if (!initializedTabs[tabName]) {
            initializedTabs[tabName] = true;
            tabsLoadFunctions[tabName]();
        }
    }

    function showTab(tabName) {
        $('.selected', tabsElt).removeClass('selected');
        $('.' + tabName, tabsElt).addClass('selected');

        loadTab(tabName);

        // Hide all panels.
        $('.panel').hide();
        // Then show the one for our tab.
        $('#' + tabName + '-panel').show();
    }

    function loadInitialTab() {
        var currentTab = window.location.hash.substring(1);

        if (!currentTab) {
            currentTab = 'reports'; // the default tab
        }

        showTab(currentTab);
    }

    function startSearchForm(callback) {
        var queryString = window.location.search.substring(1);
        var initialParams = socorro.search.parseQueryString(queryString);
        if (initialParams) {
            if (initialParams.page) {
                pageNum = initialParams.page;
            }

            initialParams = socorro.search.getFilteredParams(initialParams);
            form.dynamicForm(fieldsURL, initialParams, '#search-params-fieldset', function () {
                // When the form has finished loading, we get sanitized parameters
                // from it and show the results. This will avoid strange behaviors
                // that can be caused by manually set parameters, for example.
                callback();
            });
        }
        else {
            // No initial params, just load the form and let the user play with it.
            form.dynamicForm(fieldsURL, {}, '#search-params-fieldset');
            callback();
        }

        form.hide();
    }

    function addLoaderToElt(elt) {
        elt.append($('<div>', {class: 'loader'}));
    }

    function handleError(contentElt, jqXHR, textStatus, errorThrown) {
        var errorContent = $('<div>', {class: 'error'});

        try {
            var errorDetails = $(jqXHR.responseText); // This might fail
            var errorTitle = 'Oops, an error occured';
            var errorMsg = 'Please fix the following issues: ';

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append(errorDetails);
        }
        catch (e) {
            // If an exception occurs, that means jQuery wasn't able
            // to understand the status of the HTTP response. It is
            // probably a 500 error. We thus show a different error.
            var errorTitle = 'An unexpected error occured :(';
            var errorMsg = 'We have been automatically informed of that error, and are working on a solution. ';
            var errorDetails = textStatus + ' - ' + errorThrown;

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append($('<p>', {text: errorDetails}));
        }

        contentElt.empty().append(errorContent);
    }

    function bindEvents() {
        $('.new-line').click(function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        $('button[type=submit]', form).click(function (e) {
            e.preventDefault();
            var params = form.dynamicForm('getParams');
            var queryString = '?' + $.param(params, true);
            window.location.search = queryString;
        });

        // Change tab using navigation links.
        $('a', tabsElt).click(function (e) {
            showTab($(this).data('tab-name'));
        });

        // Show or hide filters.
        $('.toggle-filters').click(function (e) {
            e.preventDefault();

            var elt = $(this);
            form.toggle();
            elt.toggleClass('show');
            if (elt.hasClass('show')) {
                elt.html('Show');
            }
            else {
                elt.html('Hide');
            }
        });
    }

    tabsLoadFunctions.reports = function () {
        // Initialize the reports tab, bind all events and start loading
        // default data.
        var reportsPanel = $('#reports-panel');
        var contentElt = $('.content', reportsPanel);
        var columnsInput = $('input[name=_columns_fake]', reportsPanel);

        var dataUrl = reportsPanel.data('source-url');

        function prepareResultsQueryString(params) {
            var i;
            var len;

            var columns = columnsInput.select2('data');
            if (columns) {
                params._columns = [];
                for (i = 0, len = columns.length; i < len; i++) {
                    params._columns[i] = columns[i].id;
                }
            }

            // Add the page number.
            params.page = pageNum;

            var queryString = $.param(params, true);
            return '?' + queryString;
        }

        function showReports() {
            // Remove previous results and show loader.
            contentElt.empty();
            addLoaderToElt(contentElt);

            var params = form.dynamicForm('getParams');
            var url = dataUrl + prepareResultsQueryString(params);

            $.ajax({
                url: url,
                success: function(data) {
                    contentElt.empty().append($(data));
                    $('.tablesorter').tablesorter();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    handleError(contentElt, jqXHR, textStatus, errorThrown);
                },
                dataType: 'HTML'
            });
        }

        $('submit', reportsPanel).click(function (e) {
            e.preventDefault();
            showReports();
        });

        showReports();
    };

    tabsLoadFunctions.aggregations = function () {
        var aggregationsPanel = $('#aggregations-panel');
        var contentElt = $('.content', aggregationsPanel);
    };

    // Finally start the damn thing.
    bindEvents();
    startSearchForm(loadInitialTab);
});
