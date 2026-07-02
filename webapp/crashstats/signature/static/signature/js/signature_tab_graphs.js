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

// Format the data for the graph library.
SignatureReport.GraphsTab.prototype.formatData = function (data) {
  var option = data.aggregation;

  // Object map to contain data for each element
  var lineDataObject = {};
  // Array list to hold the formatted dataset
  var lineDataArray = [];
  // Array of date values for the graph's x-axis
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

    var currentDateCount = {};

    // Maps the current date's crash count to the element
    $.each(dateData.facets[option], function (j, termData) {
      currentDateCount[termData.term] = termData.count;
    });

    // Check if each top 4 element contains crashes for the current date
    $.each(lineDataObject, function (element, dataObject) {
      var crashCount = 0;

      if (Object.prototype.hasOwnProperty.call(currentDateCount, element)) {
        crashCount = currentDateCount[element];
      } else {
        crashCount = 0;
      }
      dataObject.data.push(crashCount);
    });
  });

  // Convert the data object into an array of data points for chart.js
  $.each(lineDataObject, function (fieldValue, lineData) {
    lineDataArray.push(lineData);
  });

  // Return the line data, the date labels and also any remaining terms after the
  // top 4 were spliced out.
  return { datasets: lineDataArray, labels: dateValues, missingTerms: termCounts };
};

SignatureReport.GraphsTab.prototype.drawGraph = function (graphData, contentElement) {
  // Create a canvas element for chart.js
  var graphElement = $('<canvas></canvas>');

  // Remove the loader and append divs for graph.
  contentElement.empty().append(graphElement);

  // If there are extra terms missing, let the user know.
  if (graphData.missingTerms.length) {
    var message = 'Showing the top 4 results. Not showing:';
    $.each(graphData.missingTerms, function (i, term) {
      message += ' ' + term.term + ' (' + term.count + (term.count === 1 ? ' crash),' : ' crashes),');
    });
    contentElement.append($('<p>', { text: message.slice(0, -1) }));
  }

  // Draw the graph on the canvas element using chart.js
  new Chart(graphElement, {
    type: 'line',
    data: {
      labels: graphData.labels,
      datasets: graphData.datasets,
    },
  });
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
