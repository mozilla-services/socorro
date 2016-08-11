/* global socorro:true, $:true, Analytics:true */

var SignatureReport = {
    // Function to help with inheritance.
    'inherit': function (proto) {
        var f = function () {};
        f.prototype = proto;
        return new f ();
    },
};

SignatureReport.init = function () {
    'use strict';

    // parameters
    var searchSection = $('#search-form');
    var form = $('form', searchSection);
    SignatureReport.form = form;
    var fieldsURL = form.data('fields-url');
    var SIGNATURE = form.data('signature');
    SignatureReport.signature = SIGNATURE;
    var panelsNavSection = $('#panels-nav');
    var mainBodyElt = $('#mainbody');

    SignatureReport.pageNum = 1;  // the page number as passed in the URL

    // Define the tab names.
    var tabNames = $('a', panelsNavSection).map(function () {
        return $(this).data('tab-name');
    });
    var tabs = {};
    var tabClasses = {
        'summary': SignatureReport.SummaryTab,
        'graphs': SignatureReport.GraphsTab,
        'reports': SignatureReport.ReportsTab,
        'aggregations': SignatureReport.AggregationsTab,
        'bugzilla': SignatureReport.BugzillaTab,
        'comments': SignatureReport.CommentsTab,
        'correlations': SignatureReport.CorrelationsTab,
        'graph': SignatureReport.GraphTab,
    };

    // Set the current tab, either from location.hash or defaultTab.
    var defaultTab = tabNames[0];
    var hashString = window.location.hash.substring(1);
    var currentTab = hashString ? hashString : defaultTab;

    // Helper function for getting parameters.
    SignatureReport.getParamsWithSignature = function () {
        var params = form.dynamicForm('getParams');
        params.signature = SIGNATURE;
        return params;
    };

    // Helper function for capitalizing headings.
    SignatureReport.capitalizeHeading = function (heading) {
        return heading.charAt(0).toUpperCase() +
            heading.slice(1).replace(/_/g, ' ');
    };

    // Helper function for adding a loader.
    SignatureReport.addLoaderToElement = function (elt) {
        elt.empty();
        elt.append($('<div>', {'class': 'loader'}));
    };

    SignatureReport.handleError = function (contentElt, jqXHR, textStatus, errorThrown) {
        var errorContent = $('<div>', {class: 'error'});
        var errorDetails;
        var errorTitle;
        var errorMsg;

        try {
            errorDetails = $(jqXHR.responseText); // This might fail
            errorTitle = 'Oops, an error occured';
            errorMsg = 'Please fix the following issues: ';

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append(errorDetails);
        }
        catch (e) {
            // If an exception occurs, that means jQuery wasn't able
            // to understand the status of the HTTP response. It is
            // probably a 500 error. We thus show a different error.
            errorDetails = textStatus + ' - ' + errorThrown;
            errorTitle = 'An unexpected error occured :(';
            errorMsg = 'We have been automatically informed of that error, and are working on a solution. ';

            errorContent.append($('<h3>', {text: errorTitle}));
            errorContent.append($('<p>', {text: errorMsg}));
            errorContent.append($('<p>', {text: errorDetails}));
        }

        contentElt.empty().append(errorContent);
    };

    // Manages showing a new tab and hiding the old tab.
    function showTab(tabName) {
        $('.selected', panelsNavSection).removeClass('selected');
        $('.' + tabName, panelsNavSection).addClass('selected');

        Analytics.trackTabSwitch('signature_report', tabName);

        // Hide the loading panel if it is being displayed.
        $('#loading-panel', mainBodyElt).hide();

        // Hide the previous tab and show the new tab.
        tabs[currentTab].hideTab();
        currentTab = tabName;
        tabs[currentTab].showTab();
    }

    function loadInitialTab() {
        showTab(currentTab);
    }

    function startSearchForm(callback) {
        var queryString = window.location.search.substring(1);
        var initialParams = socorro.search.parseQueryString(queryString);
        if (initialParams) {
            if (initialParams.page) {
                SignatureReport.pageNum = initialParams.page;
            }
            if (initialParams.signature) {
                delete initialParams.signature;
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

        searchSection.hide();
    }

    function bindEvents() {
        searchSection.on('click', '.new-line', function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        searchSection.on('click', 'button[type=submit]', function (e) {
            e.preventDefault();
            var params = SignatureReport.getParamsWithSignature();
            var queryString = '?' + Qs.stringify(params, { indices: false });
            window.location.search = queryString;
        });

        // Show or hide filters.
        $('.toggle-filters').on('click', function (e) {
            e.preventDefault();
            searchSection.slideToggle(300);

            // Update the main toggle link.
            var mainToggleLink = $('.display-toggle-filters');
            mainToggleLink.toggleClass('show');
            var newText = mainToggleLink.data('text-opposite');
            mainToggleLink.data('text-opposite', mainToggleLink.text());
            mainToggleLink.text(newText);
        });

        // Change tab using navigation links.
        panelsNavSection.on('click', 'a', function () {
            showTab($(this).data('tab-name'));
        });
    }

    // Make the tabs.
    $.each(tabNames, function (i, tabName) {
        var TabClass = tabClasses[tabName];
        tabs[tabName] = new TabClass(tabName);
        mainBodyElt.append(tabs[tabName].$panelElement);
    });

    // Finally start the damn thing.
    bindEvents();
    startSearchForm(loadInitialTab);
};

$(SignatureReport.init);
