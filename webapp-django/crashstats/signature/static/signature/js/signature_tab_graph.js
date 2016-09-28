/**
 * Tab for displaying crashes per ADI graph.
 * Has panels.
 * Controlled by a select.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.GraphTab = function(tabName) {

    var config = {
        'panels': true,
        'defaultOptions': ['nightly'],
        'dataDisplayType': 'graph',
        'pagination': false
    };

	SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.GraphTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

// Extends loadControls to load a select with options for each channel.
SignatureReport.GraphTab.prototype.loadControls = function() {

    // For accessing this inside functions.
    var that = this;

    // Make the select element and one empty option (for select2).
    var selectElement = $('<select>', {'class': 'channels-list'});
    selectElement.append($('<option>'));

    // Pick up necessary data from the DOM
    var channels = $('#mainbody').data('channels');

    // Make and append and option for each channel.
    $.each(channels, function (i, channel) {
        selectElement.append($('<option>', {
            'value': channel,
            'text': channel
        }));
    });

    // Append the controls.
    this.$controlsElement.append(selectElement, $('<hr>'));

    // Apply select2 to select element.
    selectElement.select2({
        'placeholder': 'Channel...',
        'allowClear': true
    });

    // Draw a new graph whenever a new channel is chosen.
    selectElement.on('change', function (e) {
        selectElement.select2('val', '');
        that.loadPanel(e.val);
    });

};

// Extends getParamsForUrl to handle two particular situations:
// 1) when multiple products are defined
// 2) when no product is defined
SignatureReport.GraphTab.prototype.getParamsForUrl = function () {

    // Get the params as usual.
    var params = SignatureReport.getParamsWithSignature();

    // If a product has been defined...
    if (params.product) {

        // ...There may be multiple products, so pick the first one.
        params.product = params.product[0];

    // If no product has been defined, the user must choose one.
    } else {

        // Show the search form.
        var searchFormLink = $('.toggle-filters');
        searchFormLink.removeClass('show');
        searchFormLink.html('Hide');
        SignatureReport.form.show();

        // Add a new fieldset for choosing a product.
        SignatureReport.form.dynamicForm('newLine', {
            field: 'product',
            operator: 'has terms',
            value: ''
        });

        // Focus the value input of the new fieldset.
        $('fieldset:last-child .value').select2('open');

        // Prompt the user to choose a product.
        this.$contentElement.empty().text('Please select a product.');

        return;

    }

    return params;

};

// Processes the data.
SignatureReport.GraphTab.prototype.formatData = function(data) {

    // Nest on build IDs and sum the counts.
    var finalData = d3.nest()
        .key(function(d) {
            return d.buildid;
        })
        .rollup(function(dlist) {
            var r = {
                adu_count: d3.sum(dlist, function(d) {
                    return d.adu_count;
                }),
                crash_count: d3.sum(dlist, function(d) {
                    return d.crash_count;
                })
            };
            if (r.adu_count) {
                r.ratio = r.crash_count / r.adu_count;
            }
            return r;
        })
        .sortKeys()
        .entries(data)
        .filter(function(d) {
            return d.values.ratio !== undefined;
        });

    // Cut off the bottom 20% of ADU counts.
    // (We do this because it has been done historically.)
    var adus = finalData.map(function(d) {
        return d.values.adu_count;
    });
    adus.sort(d3.ascending);
    var cutoff = d3.quantile(adus, 0.2);
    finalData = finalData.filter(function(d) {
        return d.values.adu_count >= cutoff;
    });

    // Reshape into the format required to draw the graph.
    finalData = finalData.map(function(d) {
        return {
            'build_id': d.key,
            'date': d.key,
            'ratio': d.values.ratio,
            'adu_count': d.values.adu_count,
            'crash_count': d.values.crash_count
        };
    });

    // Convert build IDs to dates and make the format nicer.
    MG.convert.date(finalData, 'date', '%Y%m%d%H%M%S');

    return finalData;

};

// Draws the graph.
SignatureReport.GraphTab.prototype.drawGraph = function(data, contentElement) {

    // Remove the loader and append a div for graph.
    var graphElement = $('<div>', {
        'class': 'adu-graph new-graph'
    });

    contentElement.empty().append(graphElement);

    MG.data_graphic({
        data: data,
        chart_type: 'point',
        title: 'Crashes per ADI by build ID',
        full_width: true,
        target: '.new-graph',
        x_accessor: 'date',
        y_accessor: 'ratio',
        axes_not_compact: true,
        decimals: 10,
        area: false,
        show_secondary_x_label: false,
        mouseover: function(d, i) {
            $('.mg-active-datapoint')
                .html('Build ID: ' + data[i].build_id +
                    ', ADI count: ' + data[i].adu_count +
                    ', Crash count: ' + data[i].crash_count
                );
        }
    });

    graphElement.removeClass('new-graph');

};

// Extends onAjaxSuccess to process the data and draw a graph.
SignatureReport.GraphTab.prototype.onAjaxSuccess = function (contentElement, data) {

    // If data was returned, draw the graph.
    // (NB If a product was not defined, no data will be returned here.)
    if (data.total) {
        this.drawGraph(this.formatData(data.hits), contentElement);
    // If no data was returned, let the user know.
    } else {
        contentElement.text('No results were found.');
    }

};
