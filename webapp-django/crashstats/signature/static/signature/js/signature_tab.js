/**
 * Abstract class for a tab to show information on the signature report page.
 *
 * @param {string} tabName The title that will appear at the top of the tab
 * @param {Object} config Options to configure the tab
 * @cfg {boolean} panels Whether the tab has panels
 * @cfg {Array} defaultOptions
 *      The panel(s) to display on initial load
 *      If panels is false, this should not be set
 *      If panels is true, there should be at least one default option
 *      (It is assumed that if there are panels, there is a select)
 * @cfg {string} dataDisplayType 'graph' or 'table'
 * @cfg {boolean} pagination
 *      Should be true if the tab is displaying tables with pages
 */
SignatureReport.Tab = function (tabName, config) {

    // Set the name of the tab.
    this.tabName = tabName;

    // Set the configurations.
    config = config || {};
    this.panels = config.panels;
    this.defaultOptions = config.defaultOptions;
    this.dataDisplayType = config.dataDisplayType;
    this.pagination = config.pagination;
    this.page = SignatureReport.pageNum;

    // Tab is not loaded until this.showTab is called.
    this.loaded = false;
    this.dataUrl = SignatureReport.getURL(this.tabName);

    // Make the HTML elements.
    this.$panelElement = $('<section>',
        {'class': 'panel tab-panel ' + this.tabName + '-panel'}
    );
    var $headerElement = $('<header>', {'class': 'title'});
    var $headingElement = $('<h2>', {
        'text': SignatureReport.capitalizeHeading(this.tabName)}
    );
    var $bodyElement = $('<div>', {'class': 'body'});
    this.$controlsElement = $('<div>', {'class': 'controls'});
    this.$contentElement = $('<div>', {'class': 'content'});

    // Append the elements.
    this.$panelElement.append(
        $headerElement.append(
            $headingElement
        ),
        $bodyElement.append(
            this.$controlsElement,
            this.$contentElement
        )
    );

};

/*
 *  Functions for managing the tab display.
 */

// Shows the tab. Also loads it if it is not already loaded.
SignatureReport.Tab.prototype.showTab = function () {

    // If tab hasn't been loaded, load it.
    if (!this.loaded) {

        // Load the controls.
        // (If there are no controls this won't do anything.)
        this.loadControls();

        // Next load the content.
        // If there are no panels, load the content directly.
        if (!this.panels) {
            this.loadContent(this.$contentElement);
        // If there are panels, load the default panels.
        // (loadContent will be called by loadPanel.)
        } else {
            for (var i = 0; i < this.defaultOptions.length; i++ ) {
                this.loadPanel(this.defaultOptions[i]);
            }
        }

        // Record that this tab has now been loaded.
        this.loaded = true;

    }

    // Show this tab.
    this.$panelElement.show();

};

// Hides the tab.
SignatureReport.Tab.prototype.hideTab = function () {
    this.$panelElement.hide();
};

/*
 *  Functions for loading the content.
 */

// Extend this to load any controls.
SignatureReport.Tab.prototype.loadControls = function () {
    // If there are no controls, nothing will happen.
};

// Extend this if any extra parameters need to be added.
SignatureReport.Tab.prototype.getParamsForUrl = function () {
    var params = SignatureReport.getParamsWithSignature();
    if (this.pagination) {
        params.page = this.page || SignatureReport.pageNum;
    }
    return params;
};

// Extend this if anything different needs to be added to the URL.
SignatureReport.Tab.prototype.buildUrl = function (params, option) {
    option = option ? option + '/' : '';
    return this.dataUrl + option + '?' + Qs.stringify(params, { indices: false });
};

// Extend this if anything different should be done with the returned data.
SignatureReport.Tab.prototype.onAjaxSuccess = function (contentElement, data) {
    contentElement.empty().append($(data));
    if (this.dataDisplayType === 'table') {
        $('.tablesorter').tablesorter();
    }
    if (this.pagination) {
        this.bindPaginationLinks(contentElement);
    }
};

// This should not need to be extended.
// NB if panels are present, the tab is assumed to have a select as its controls.
SignatureReport.Tab.prototype.loadPanel = function (option) {

    // Initialize a new panel.
    var panel = new SignatureReport.Panel(
        option,
        $.proxy(function () {
            $('option[value=' + option + ']', this.$selectElement).prop('disabled', false);
        }, this)
    );

    // Append the new panel.
    this.$contentElement.append(panel.$panelElement);

    // Disable the currently selected option.
    $('option[value=' + option + ']', this.$selectElement).prop('disabled', true);

    // Now load the panel's content.
    this.loadContent(panel.$contentElement, option);

};

// This should not need to be extended.
SignatureReport.Tab.prototype.loadContent = function (contentElement, option) {

    // Get the parameters for the URL to get the data.
    var params = this.getParamsForUrl();

    if (params) {

        // Make the URL for getting the data.
        var url = this.buildUrl(params, option);

        // Define the returned data type according to whether we are getting a
        // table or a graph.
        var dataTypes = {
            'table': 'html',
            'graph': 'json'
        };

        // Empty the content element and append a loader.
        SignatureReport.addLoaderToElement(contentElement);

        // Request the data.
        $.ajax({
            url: url,
            success: $.proxy(this.onAjaxSuccess, this, contentElement),
            error: function(jqXHR, textStatus, errorThrown) {
                SignatureReport.handleError(contentElement, jqXHR, textStatus, errorThrown);
            },
            dataType: dataTypes[this.dataDisplayType]
        });

    }

};

// This should not need to be extended.
SignatureReport.Tab.prototype.bindPaginationLinks = function (contentElement) {

    // For accessing this inside functions.
    var that = this;

    $('.pagination a', contentElement).click(function (e) {
        e.preventDefault();

        that.page = $(this).data('page');
        that.loadContent(contentElement);
    });

};
