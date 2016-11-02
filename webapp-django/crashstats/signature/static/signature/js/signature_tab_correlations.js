/*global SignatureReport */

/**
 * Tab for displaying correlations.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.CorrelationsTab = function (tabName) {

    var config  = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': false,
    };

    SignatureReport.Tab.call(this, tabName, config);

};

SignatureReport.CorrelationsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.CorrelationsTab.prototype.loadControls = function() {
    var self = this;

    var defaultProduct = $('#mainbody').data('default-product');
    var defaultChannel = $('#mainbody').data('default-channel');
    var channels = $('#mainbody').data('channels');

    // Create a select box for the product.
    this.productSelect = $('<select>', {'class': 'products-list', id: 'correlations-products-list'});
    this.productSelect.append($('<option>', { value: 'Firefox', text: 'Firefox'}));
    this.productSelect.append($('<option>', { value: 'FennecAndroid', text: 'FennecAndroid'}));

    // Create a select box for the channel.
    this.channelSelect = $('<select>', {'class': 'channels-list', id: 'correlations-channels-list'});
    channels.forEach(function (channel) {
        if (channel === 'esr') {
            // This correlations module doesn't support ESR releases.
            return;
        }
        self.channelSelect.append($('<option>', {
            'value': channel,
            'text': channel,
        }));
    });

    // Append the controls.
    this.$controlsElement.append(
        $('<label>', {for: 'correlations-products-list', text: 'Product: '}),
        this.productSelect,
        $('<label>', {for: 'correlations-channels-list', text: 'Channel: '}),
        this.channelSelect,
        $('<hr>')
    );

    // Apply select2 to both select elements and give them a default value.
    this.productSelect.select2();
    this.productSelect.select2('val', defaultProduct);

    this.channelSelect.select2();
    this.channelSelect.select2('val', defaultChannel);

    this.productSelect.on('change', this.loadCorrelations.bind(this));
    this.channelSelect.on('change', this.loadCorrelations.bind(this));
};

SignatureReport.CorrelationsTab.prototype.onAjaxSuccess = function () {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

    this.loadCorrelations();
};

SignatureReport.CorrelationsTab.prototype.loadCorrelations = function () {
    var contentElt = $('#correlations-wrapper pre');
    contentElt.empty().append($('<div>', {'class': 'loader'}));

    var product = this.productSelect.select2('val');
    var channel = this.channelSelect.select2('val');

    $('#correlations-wrapper h3').text('Correlations for ' + product + ' ' + channel[0].toUpperCase() + channel.substr(1));

    window.correlations.getCorrelations(SignatureReport.signature, channel, product)
    .then(function (results) {
        var content = results;
        if (Array.isArray(results)) {
            content = results.join('\n');
        }
        contentElt.empty().append(content);
    });
};
