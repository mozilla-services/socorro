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

    this.$sortInputHidden = $('<input>', {
        'type': 'hidden',
        'name': '_sort',
        'value': window.SORT
    });

    var updateButton = $('<button>', {
        'type': 'submit',
        'text': 'Update'
    });

    // Append the controls.
    this.$controlsElement.append(
        this.$sortInputHidden,
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

    // Get the sort for the input.
    var sortArr = this.$sortInputHidden.val().split(',');
    if (sortArr.length === 1 && !sortArr[0]) {
        sortArr = [];
    }

    if (sortArr) {
        params._sort = sortArr;
    }

    // Get the page number.
    params.page = this.page || SignatureReport.pageNum;

    return params;
};

// Extends buildUrl to also replace the history.
SignatureReport.ReportsTab.prototype.buildUrl = function (params) {

    // Build the query string.
    var queryString = '?' + Qs.stringify(params, { indices: false });

    // Replace the history.
    window.history.replaceState(params, null, queryString);

    // Return the whole URL.
    return this.dataUrl + queryString;
};

SignatureReport.ReportsTab.prototype.onAjaxSuccess = function (contentElement, data) {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);
    var that = this;

    $('.sort-header', contentElement).each(function() {
        $(this).click(function(event) {
            event.preventDefault();

            var thisElt = $(this);

            function removeFromArray(elt, arr) {
                var index = arr.indexOf(elt);
                if (index > -1) {
                    arr.splice(index, 1);
                }
                return arr;
            }

            // Update the sort field.
            var fieldName = thisElt.data('field-name');
            var sortArr = that.$sortInputHidden.val().split(',');

            // First remove all previous mentions of that field.
            removeFromArray(fieldName, sortArr);
            removeFromArray('-' + fieldName, sortArr);

            // Now add it in the order that follows this sequence:
            // ascending -> descending -> none
            if (thisElt.hasClass('headerSortDown')) {
                sortArr.push('-' + fieldName);
            }
            else if (!thisElt.hasClass('headerSortDown') && !thisElt.hasClass('headerSortUp')) {
                sortArr.push(fieldName);
            }

            that.$sortInputHidden.val(sortArr.join(','));

            that.loadContent(that.$contentElement);
        });
    });

};
