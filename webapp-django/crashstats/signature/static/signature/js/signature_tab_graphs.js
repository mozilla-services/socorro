/**
 * Tab for displaying graphs.
 * Has panels.
 * Controlled by select.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.GraphsTab = function(tabName) {

    var config  = {
        'panels': true,
        'dataDisplayType': 'graph',
        'defaultOptions': ['product'],
        'pagination': false
    };

    SignatureReport.Tab.call(this, tabName, config);

};

SignatureReport.GraphsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.GraphsTab.prototype.loadControls = function () {

    // For accessing this inside functions.
    var that = this;

    // Make the select element and one empty option element (for select2).
    this.$selectElement = $('<select>', {'class': 'fields-list'});
    this.$selectElement.append($('<option>'));

    // Append an option element for each field.
    $.each(window.FIELDS, function(i, field) {
        that.$selectElement.append($('<option>', {
            'value': field.id,
            'text': field.text
        }));
    });

    // Append the control elements.
    this.$controlsElement.append(this.$selectElement, $('<hr>'));

    // Set the placeholder.
    this.$selectElement.select2({
        'placeholder': 'Crashes per day, by...',
        'allowClear': true,
        'sortResults': socorro.search.sortResults,
    });

    // On changing the selected option, load a new panel.
    this.$selectElement.on('change', function (e) {
        that.$selectElement.select2('val', '');
        that.loadPanel(e.val);
    });

};

// Format the data for the graph library.
SignatureReport.GraphsTab.prototype.formatData = function (data) {

    var option = data.aggregation;

    // Variables for the graph's data and legend. Metrics Graphics requires an
    // array containing arrays of data for each line of the multi-line graph.
    var lineDataObject = {};
    var lineDataArray = [];
    var legend = [];

    // Array of objects containing the count for each term, in descending order
    // of counts.
    var termCounts = data.term_counts;

    // Splice out terms with the highest counts (up to the 4th highest) and:
    // 1) add an empty array for each one to lineDataObject
    // 2) add each one to the legend array
    $.each(termCounts.splice(0, 4), function (i, element) {
        lineDataObject[element.term] = [];
        legend.push(element.term);
    });

    // Each object in data.aggregates contains data for one date.
    $.each(data.aggregates, function (i, dateData) {

        // Each object in dateData.facets[option] contains data for one term
        // on this date.
        $.each(dateData.facets[option], function (j, termData) {

            // If this term is one of the 4 with the highest counts...
            if (lineDataObject.hasOwnProperty(termData.term)) {

                // ...Make a data object for a node on the graph...
                var nodeData = {
                    'count': termData.count,
                    'date': new Date(dateData.term),
                    'term': termData.term
                };

                // ... And add it to this term's data array.
                lineDataObject[termData.term].push(nodeData);
            }

        });

    });

    // Make the data object into an array of arrays for Metrics Graphics.
    $.each(lineDataObject, function (key, lineData) {
        lineDataArray.push(lineData);
    });

    // Return the line data, the legend and also any remaining terms after the
    // top 4 were spliced out.
    return {'data': lineDataArray, 'legend': legend, 'missingTerms': termCounts};

};

SignatureReport.GraphsTab.prototype.drawGraph = function (graphData, contentElement) {

    var graphElement = $('<div>', {
        'class': 'new-graph'
    });

    var legendElement = $('<div>', {
        'class': 'legend new-legend'
    });

    // Remove the loader and append divs for graph and legend.
    contentElement.empty().append(
        graphElement,
        legendElement
    );

    // If there are extra terms missing, let the user know.
    if (graphData.missingTerms.length) {
        var message = 'Showing the top 4 results. Not showing:';
        $.each(graphData.missingTerms, function (i, term) {
            message += ' ' + term.term + ' (' + term.count +
                (term.count === 1 ? ' crash),' : ' crashes),');
        });
        contentElement.append($('<p>', {'text': message.slice(0, -1)}));
    }

    MG.data_graphic({
        data: graphData.data,
        full_width: true,
        target: '.new-graph',
        x_accessor: 'date',
        y_accessor: 'count',
        axes_not_compact: true,
        utc_time: true,
        interpolate: 'basic',
        area: false,
        legend: graphData.legend,
        legend_target: '.new-legend',
        show_secondary_x_label: false,
        mouseover: function(d, i) {
            $('.mg-active-datapoint', contentElement)
                .html(d.term +
                    ': ' +
                    d.count +
                    (d.count === 1 ? ' crash' : ' crashes')
                );
        }
    });

    // Ensure the next graph and legend don't get added to this panel.
    graphElement.removeClass('new-graph');
    legendElement.removeClass('new-legend');

};

// Extends onAjaxSuccess to process the data and draw a graph.
SignatureReport.GraphsTab.prototype.onAjaxSuccess = function (contentElement, data) {

    // Data needs to be processed to determine if we can draw the graph.
    var graphData = this.formatData(data);

    // If data was returned, draw the graph.
    if (graphData.data.length) {
        this.drawGraph(graphData, contentElement);
    // If no data was returned, let the user know.
    } else {
        contentElement.text('No results were found.');
    }

};
