/* global SignatureReport */

/**
 * Tab for displaying correlations.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.CorrelationsTab = function (tabName) {
  var config = {
    panels: false,
    dataDisplayType: 'table',
    pagination: false,
  };

  SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.CorrelationsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.CorrelationsTab.prototype.loadControls = function () {
  var self = this;

  // Create a select box for the product.
  var correlationsProducts = $('#mainbody').data('correlations-products');
  this.productSelect = $('<select>', { class: 'products-list', id: 'correlations-products-list' });
  correlationsProducts.forEach(function (product) {
    self.productSelect.append($('<option>', { value: product, text: product }));
  });

  // Create a select box for the channel.
  var channels = $('#mainbody').data('channels');
  this.channelSelect = $('<select>', { class: 'channels-list', id: 'correlations-channels-list' });
  channels.forEach(function (channel) {
    self.channelSelect.append($('<option>', { value: channel, text: channel }));
  });

  // Append the controls.
  this.$controlsElement.append(
    $('<label>', { for: 'correlations-products-list', text: 'Product: ' }),
    this.productSelect,
    $('<label>', { for: 'correlations-channels-list', text: 'Channel: ' }),
    this.channelSelect,
    $('<hr>')
  );

  // Apply select2 to both select elements.
  this.productSelect.select2();
  this.channelSelect.select2();

  this.productSelect.on('change', this.loadCorrelations.bind(this));
  this.channelSelect.on('change', this.loadCorrelations.bind(this));
};

SignatureReport.CorrelationsTab.prototype.onAjaxSuccess = function () {
  SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

  var defaultProduct = $('#correlations-wrapper').data('default-product');
  var defaultChannel = $('#correlations-wrapper').data('default-channel');

  // Give the select elements a default value.
  this.productSelect.select2('val', defaultProduct);
  this.channelSelect.select2('val', defaultChannel);

  this.loadCorrelations();
};

SignatureReport.CorrelationsTab.prototype.loadCorrelations = function () {
  var contentElt = $('#correlations-wrapper pre');
  contentElt.empty().append($('<div>', { class: 'loader' }));

  var product = this.productSelect.select2('val');
  var channel = this.channelSelect.select2('val');

  $('#correlations-wrapper h3').text(
    'Correlations for ' + product + ' ' + channel[0].toUpperCase() + channel.substr(1)
  );

  window.correlations.getCorrelations(SignatureReport.signature, channel, product).then(function (results) {
    var content = results;
    if (Array.isArray(results)) {
      contentElt.empty();
      for (var i = 0; i < results.length; i++) {
        contentElt.append(document.createTextNode(results[i]));
        contentElt.append(document.createElement('br'));
      }
    } else {
      contentElt.empty().text(content);
    }
  });
};
