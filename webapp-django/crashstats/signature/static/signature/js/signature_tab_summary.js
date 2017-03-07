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

SignatureReport.SummaryTab.prototype.onAjaxSuccess = function (contentElement, data) {
    SignatureReport.Tab.prototype.onAjaxSuccess.apply(this, arguments);

    var localStorageKey = 'pref-opened-panels';
    var prefOpenedPanels = JSON.parse(localStorage.getItem(localStorageKey) || '[]');
    prefOpenedPanels.forEach(function(id, i) {
        var parent = $('#' + id + '.panel');
        $('.content', parent).toggle();
        $('.options', parent).toggleClass('hide');
    });

    $(contentElement).on('click', '.panel header', function (e) {
        e.preventDefault();
        var parent = $(this).parent();
        var panelId = parent.attr('id');
        if ($('.content:visible', parent).length) {
            prefOpenedPanels.splice(prefOpenedPanels.indexOf(panelId), 1);
        } else {
            prefOpenedPanels.push(panelId);
        }
        localStorage.setItem(localStorageKey, JSON.stringify(prefOpenedPanels));
        $('.content', parent).toggle();
        $('.options', this).toggleClass('hide');
    });
};
