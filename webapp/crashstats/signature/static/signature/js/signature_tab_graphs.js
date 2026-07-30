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
  for (var field of fields) {
    that.$selectElement.append(
      $('<option>', {
        value: field.id,
        text: field.text,
      })
    );
  }

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

// Format the data for the graph library.
SignatureReport.GraphsTab.prototype.formatData = function (data) {
  var option = data.aggregation;

  // Get the top 4 elements of the crash data
  var datasets = data.term_counts.splice(0, 4).map((element) => ({
    label: element.term,
  }));

  // Array of date values in month, day format
  var dateValues = data.aggregates.map((dateData) =>
    new Date(dateData.term).toLocaleDateString('en-US', {
      timeZone: 'UTC',
      month: 'long',
      day: 'numeric',
    })
  );

  // Build a dictionary for crash counts based on date and aggregation type
  var crashData = {};
  for (var dateData of data.aggregates) {
    crashData[dateData.term] = {};
    for (var item of dateData.facets[option]) {
      crashData[dateData.term][item.term] = item.count;
    }
  }

  // Add the crash counts to the dataset
  for (var dataset of datasets) {
    dataset.data = data.aggregates.map((dateData) => crashData[dateData.term][dataset.label] || 0);
  }

  // Return the line data, the date labels and also any remaining terms after the
  // top 4 were spliced out.
  return { datasets, labels: dateValues, missingTerms: data.term_counts };
};

SignatureReport.GraphsTab.prototype.drawGraph = function (graphData, contentElement) {
  // Create a div container for the graphElement
  var graphContainer = $('<div>', {
    style: 'height: 250px',
  });

  // Create a canvas element for chart.js
  var graphElement = $('<canvas></canvas>');

  graphContainer.append(graphElement);

  // Remove the loader and append divs for graph.
  contentElement.empty().append(graphContainer);

  // If there are extra terms missing, let the user know.
  if (graphData.missingTerms.length) {
    var message = 'Showing the top 4 results. Not showing:';
    for (var term of graphData.missingTerms) {
      message += ' ' + term.term + ' (' + term.count + (term.count === 1 ? ' crash),' : ' crashes),');
    }
    contentElement.append($('<p>', { text: message.slice(0, -1) }));
  }

  // Draw the graph on the graphElement using chart.js
  var chart = new Chart(graphElement, {
    type: 'line',
    data: {
      labels: graphData.labels,
      datasets: graphData.datasets,
    },
    options: {
      maintainAspectRatio: false,
      elements: {
        point: {
          radius: 0,
          hitRadius: 20,
          hoverRadius: 4,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
        },
        x: {
          ticks: {
            autoSkip: true,
            maxTicksLimit: 10,
          },
        },
      },
    },
  });

  contentElement.data('chart', chart);
};

// Extends onAjaxSuccess to process the data and draw a graph.
SignatureReport.GraphsTab.prototype.onAjaxSuccess = function (contentElement, data) {
  // Data needs to be processed to determine if we can draw the graph.
  var graphData = this.formatData(data);

  // If data was returned, draw the graph.
  if (graphData.datasets.length) {
    this.drawGraph(graphData, contentElement);
    // If no data was returned, let the user know.
  } else {
    contentElement.text('No results were found.');
  }
};
