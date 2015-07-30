/**
 * Tab for displaying comments table.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.CommentsTab = function(tabName) {

    var config  = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': true
    };

    SignatureReport.Tab.call(this, tabName, config);

};

SignatureReport.CommentsTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);
