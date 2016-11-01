/*global SignatureReport: true */
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

SignatureReport.CorrelationsTab.prototype.onAjaxSuccess = function () {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

    function load() {
        var product = $('#correlations_product').val();
        var channel = $('#correlations_channel').val();

        $('#correlations_desc').text('Correlations for ' + product + ' ' + channel[0].toUpperCase() + channel.substr(1));

        window.correlations.writeResults($('#correlations_results'), SignatureReport.signature, channel, product);
    }

    load();
    $('#correlations_product').change(load);
    $('#correlations_channel').change(load);
};
