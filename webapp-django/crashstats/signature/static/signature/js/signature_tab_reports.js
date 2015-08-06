/**
 * Tab for displaying reports table.
 * Does not have any panels.
 * Controlled by a text input.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.ReportsTab = function(tabName) {

    var config = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': true
    };

    SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.ReportsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

// Extends loadControls to add a text input and some default fields.
SignatureReport.ReportsTab.prototype.loadControls = function() {

    // For accessing this inside functions.
    var that = this;

    // Make the control elements: an input and an update button.
    // (The hidden input is for select2.)
    var columnsInputHidden = $('<input>',  {
        'type': 'hidden',
        'name': '_columns',
        'value': window.COLUMNS
    });

    this.$columnsInput = $('<input>', {
        'type': 'text',
        'name': '_columns_fake',
        'value': window.COLUMNS
    });

    var updateButton = $('<button>', {
        'type': 'submit',
        'text': 'Update'
    });

    // Append the controls.
    this.$controlsElement.append(
        this.$columnsInput,
        columnsInputHidden,
        updateButton,
        $('<hr>')
    );

    // Make the columns input sortable.
    this.$columnsInput.select2({
        'data': window.FIELDS,
        'multiple': true,
        'width': 'element'
    });

    this.$columnsInput.on("change", function() {
        columnsInputHidden.val(that.$columnsInput.val());
    });

    this.$columnsInput.select2('container').find('ul.select2-choices').sortable({
        containment: 'parent',
        start: function() {
            that.$columnsInput.select2('onSortStart');
        },
        update: function() {
            that.$columnsInput.select2('onSortEnd');
        }
    });

    // On clicking the update button, loadContent is called.
    updateButton.on('click', function (e) {
        e.preventDefault();
        that.loadContent(that.$contentElement);
    });

};

// Extends getParamsForUrl to do two extra things:
// 1) add the columns parameters
// 2) add the page parameter
SignatureReport.ReportsTab.prototype.getParamsForUrl = function () {

    // Get the params as usual.
    var params = SignatureReport.getParamsWithSignature();

    // Get the columns for the input.
    var columns = this.$columnsInput.select2('data');
    if (columns) {
        params._columns = $.map(columns, function(column) {
            return column.id;
        });
    }

    // Get the page number.
    params.page = this.page || SignatureReport.pageNum;

    return params;

};

// Extends buildUrl to also replace the history.
SignatureReport.ReportsTab.prototype.buildUrl = function (params) {

    // Build the query string.
    var queryString = '?' + $.param(params, true);

    // Replace the history.
    window.history.replaceState(params, null, queryString);

    // Return the whole URL.
    return this.dataUrl + queryString;

};
