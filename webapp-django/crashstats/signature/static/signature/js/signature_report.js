/* global socorro:true, $:true */

window.SignatureReport = {

    // Function to help with inheritance.
    'inherit': function (proto) {
        var f = function () {};
        f.prototype = proto;
        return new f ();
    }

};

SignatureReport.init = function () {
    'use strict';

    // parameters
    var searchSection = $('#search-form');
    var form = $('form', searchSection);
    SignatureReport.form = form;
    var fieldsURL = form.data('fields-url');
    var SIGNATURE = form.data('signature');
    var panelsNavSection = $('#panels-nav');
    var mainBodyElt = $('#mainbody');

    SignatureReport.pageNum = 1;  // the page number as passed in the URL

    // Define the tab names.
    var tabNames = ['summary', 'graphs', 'reports', 'aggregations', 'comments', 'bugzilla', 'graph'];
    var tabs = {};
    var tabClasses = {
        'summary': SignatureReport.SummaryTab,
        'graphs': SignatureReport.GraphsTab,
        'reports': SignatureReport.ReportsTab,
        'aggregations': SignatureReport.AggregationsTab,
        'comments': SignatureReport.CommentsTab,
        'bugzilla': SignatureReport.BugzillaTab,
        'graph': SignatureReport.GraphTab
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

        form.hide();
    }

    function bindEvents() {
        searchSection.on('click', '.new-line', function (e) {
            e.preventDefault();
            form.dynamicForm('newLine');
        });

        searchSection.on('click', 'button[type=submit]', function (e) {
            e.preventDefault();
            var params = SignatureReport.getParamsWithSignature();
            var queryString = '?' + $.param(params, true);
            window.location.search = queryString;
        });

        // Show or hide filters.
        searchSection.on('click', '.toggle-filters', function (e) {
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

        // Change tab using navigation links.
        panelsNavSection.on('click', 'a', function (e) {
            showTab($(this).data('tab-name'));
        });
    }

    // Make the tabs.
    $.each(tabNames, function(i, tabName) {
        var TabClass = tabClasses[tabName];
        tabs[tabName] = new TabClass(tabName);
        mainBodyElt.append(tabs[tabName].$panelElement);
    });

    // Finally start the damn thing.
    bindEvents();
    startSearchForm(loadInitialTab);
};

$(SignatureReport.init);
