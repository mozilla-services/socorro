/**
 * Tab for displaying Bugzilla table.
 * Does not have any panels.
 * Does not have any controls.
 *
 * @extends {SignatureReport.Tab}
 * @inheritdoc
 */
SignatureReport.BugzillaTab = function(tabName) {

    var config  = {
        'panels': false,
        'dataDisplayType': 'table',
        'pagination': false
    };

    SignatureReport.Tab.call(this, tabName, config);

};

SignatureReport.BugzillaTab.prototype = SignatureReport.inherit(SignatureReport.Tab.prototype);

SignatureReport.BugzillaTab.prototype.onAjaxSuccess = function (contentElement, data) {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

    // Enhance bug links.
    BugLinks.enhance();
};
