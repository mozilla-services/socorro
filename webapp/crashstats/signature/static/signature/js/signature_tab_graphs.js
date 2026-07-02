/* global SignatureReport */

import { socorro } from '../../../../crashstats/static/crashstats/js/socorro/utils.js';
import Chart from 'chart.js/auto';

/**
 * Tab for displaying graphs.
 * Has panels.
 * Controlled by select.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.GraphsTab = function (tabName) {
  var config = {
    panels: true,
    dataDisplayType: 'graph',
    defaultOptions: ['product'],
    pagination: false,
  };

  SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.GraphsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.GraphsTab.prototype.loadControls = function () {
  // For accessing this inside functions.
  var that = this;

  // Make the select element and one empty option element (for select2).
  this.$selectElement = $('<select>', { class: 'fields-list' });
  this.$selectElement.append($('<option>'));

  // Pick up necessary data from the DOM
  var fields = $('#mainbody').data('fields');

  // Append an option element for each field.
  $.each(fields, function (i, field) {
    that.$selectElement.append(
      $('<option>', {
        value: field.id,
        text: field.text,
      })
    );
  });

  // Append the control elements.
  this.$controlsElement.append(this.$selectElement, $('<hr>'));

  // Set the placeholder.
  this.$selectElement.select2({
    placeholder: 'Crashes per day, by...',
    allowClear: true,
    sortResults: socorro.search.sortResults,
  });

  // On changing the selected option, load a new panel.
  this.$selectElement.on('change', function (e) {
    that.$selectElement.select2('val', '');
    that.loadPanel(e.val);
  });
};

// TODO: I need to rework the function below since metrics-graphics and chart.js
// don't accept the same dataset
// NOTE: update comments after

// Format the data for the graph library.
SignatureReport.GraphsTab.prototype.formatData = function (data) {
  var option = data.aggregation;

  // Variables for the graph's data and legend. Metrics Graphics requires an
  // array containing arrays of data for each line of the multi-line graph.
  var lineDataObject = {};
  var lineDataArray = [];

  // Array of dates for the data
  var dateValues = [];

  // Array of objects containing the count for each term, in descending order
  // of counts.
  var termCounts = data.term_counts;

  // By reading back innerHTML, the browser serializes the text node
  // into safe HTML thus escaping special characters.
  function escapeHTML(str) {
    let tmpDiv = document.createElement('div');
    tmpDiv.textContent = str;
    return tmpDiv.innerHTML;
  }

  $.each(termCounts.splice(0, 4), function (i, element) {
    lineDataObject[element.term] = {
      label: escapeHTML(element.term),
      data: [],
    };
  });

  // Each object in data.aggregates contains data for one date.
  $.each(data.aggregates, function (i, dateData) {
    dateValues.push(dateData.term);

    $.each(lineDataObject, function (termName, dataObject) {
      var crashCount = 0;

      $.each(dateData.facets[option], function (j, termData) {
        if (termData.term == termName) {
          crashCount = termData.count;
        }
      });
      dataObject.data.push(crashCount);
    });
  });

  // Make the data object into an array of arrays for Metrics Graphics
  // and add the associated legend in the same order.
  // The keys of lineDataObject are crash report field values
  $.each(lineDataObject, function (fieldValue, lineData) {
    lineDataArray.push(lineData);
  });

  // Return the line data, the legend and also any remaining terms after the
  // top 4 were spliced out.
  return { datasets: lineDataArray, labels: dateValues, missingTerms: termCounts };
};

SignatureReport.GraphsTab.prototype.drawGraph = function (graphData, contentElement) {
  var graphElement = $('<div>', {
    class: 'new-graph',
  });

  var legendElement = $('<div>', {
    class: 'legend new-legend',
  });

  // Remove the loader and append divs for graph and legend.
  contentElement.empty().append(graphElement, legendElement);

  // If there are extra terms missing, let the user know.
  if (graphData.missingTerms.length) {
    var message = 'Showing the top 4 results. Not showing:';
    $.each(graphData.missingTerms, function (i, term) {
      message += ' ' + term.term + ' (' + term.count + (term.count === 1 ? ' crash),' : ' crashes),');
    });
    contentElement.append($('<p>', { text: message.slice(0, -1) }));
  }
  /*
  MG.data_graphic({
    data: graphData.data,
    full_width: true,
    target: '.new-graph',
    x_accessor: 'date',
    y_accessor: 'count',
    axes_not_compact: true,
    utc_time: true,
    interpolate: d3.curveLinear,
    area: false,
    legend: graphData.legend,
    legend_target: '.new-legend',
    show_secondary_x_label: false,
    mouseover: function (d) {
      $('.mg-active-datapoint', contentElement).text(d.term + ': ' + d.count + (d.count === 1 ? ' crash' : ' crashes'));
    },
  });
*/
  // Ensure the next graph and legend don't get added to this panel.
  graphElement.removeClass('new-graph');
  legendElement.removeClass('new-legend');
};

// Extends onAjaxSuccess to process the data and draw a graph.
SignatureReport.GraphsTab.prototype.onAjaxSuccess = function (contentElement, data) {
  // Data needs to be processed to determine if we can draw the graph.
  var graphData = this.formatData(data);

  // eslint-disable-next-line no-console
  console.log(JSON.stringify(graphData));

  // If data was returned, draw the graph.
  if (graphData.datasets.length) {
    this.drawGraph(graphData, contentElement);
    // If no data was returned, let the user know.
  } else {
    contentElement.text('No results were found.');
  }
};
