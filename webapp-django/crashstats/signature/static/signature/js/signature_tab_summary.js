/**
 * Tab for displaying signature summary.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.SummaryTab = function(tabName) {

    var config  = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': false
    };

    SignatureReport.Tab.call(this, tabName, config);
};

SignatureReport.SummaryTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);
