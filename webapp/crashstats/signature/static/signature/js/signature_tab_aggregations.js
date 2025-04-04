/* global SignatureReport */

import { socorro } from '../../../../crashstats/static/crashstats/js/socorro/utils.js';

/**
 * Tab for displaying aggregations tables.
 * Has panels.
 * Controlled by a select.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.AggregationsTab = function (tabName) {
  var config = {
    panels: true,
    defaultOptions: ['product', 'platform', 'build_id', 'install_time'],
    dataDisplayType: 'table',
    pagination: false,
  };

  SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.AggregationsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

// Extends loadControls to add a select and some options.
SignatureReport.AggregationsTab.prototype.loadControls = function () {
  // For accessing this inside functions.
  var that = this;

  // Make the select element and one empty option element (for select2).
  this.$selectElement = $('<select>', { class: 'fields-list' });
  this.$selectElement.append($('<option>'));

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
    placeholder: 'Aggregate on...',
    allowClear: true,
    sortResults: socorro.search.sortResults,
  });

  // On changing the selected option, load a new panel.
  this.$selectElement.on('change', function (e) {
    that.$selectElement.select2('val', '');
    that.loadPanel(e.val);
  });
};
