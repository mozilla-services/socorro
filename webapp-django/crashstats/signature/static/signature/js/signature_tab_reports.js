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
        'width': 'element',
        'sortResults': socorro.search.sortResults,
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
    params._sort = this.$sortInputHidden.val().trim().split(',') || [];

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
    var tab = this;

    contentElement.empty().append($(data));
    $('#reports-list').tablesorter({
        headers: {
            0: {  // disable the first column, `Crash ID`
                sorter: false
            }
        }
    });
    this.bindPaginationLinks(contentElement);

    // Make sure there are more than 1 page of results. If not,
    // do not activate server-side sorting, rely on the
    // default client-side sorting.
    if ($('.pagination a', contentElement).length) {
        $('.sort-header', contentElement).click(function (e) {
            e.preventDefault();

            var thisElt = $(this);

            // Update the sort field.
            var fieldName = thisElt.data('field-name');
            var sortArr = tab.$sortInputHidden.val().split(',');

            // First remove all previous mentions of that field.
            sortArr = sortArr.filter(function (item) {
                return item !== fieldName && item !== '-' + fieldName;
            });

            // Now add it in the order that follows this sequence:
            // ascending -> descending -> none
            if (thisElt.hasClass('headerSortDown')) {
                sortArr.unshift('-' + fieldName);
            }
            else if (!thisElt.hasClass('headerSortDown') && !thisElt.hasClass('headerSortUp')) {
                sortArr.unshift(fieldName);
            }

            tab.$sortInputHidden.val(sortArr.join(','));

            tab.loadContent(tab.$contentElement);
        });
    }
};
