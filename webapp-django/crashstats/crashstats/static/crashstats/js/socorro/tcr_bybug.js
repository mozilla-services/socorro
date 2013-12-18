/*global $:false */
$(function() {
    'use strict';
    var signatureDetails = $('#signature-details');

    signatureDetails.on('click', '.toggle-sig-details', function(event) {
        event.preventDefault();

        $(this).toggleClass('expanded');

        var parentContainer = $(this).parents('table');
        var expandedState = parentContainer.attr('aria-expanded') === 'true' ? 'false' : 'true';

        parentContainer.toggleClass('initially-hidden');
        parentContainer.attr('aria-expanded', expandedState);
    });

    var bugSignatures = $('#bug_signatures');
    var pattern = /^\d+$/g;

    bugSignatures.submit(function(event) {
        var bugNumber = $.trim($('#bug_number').val());

        if (pattern.test(bugNumber)) {
            socorro.ui.removeUserMsg('#signature-details');
        } else {
            event.preventDefault();

            var response = {
                status: 'error',
                message: 'Only numbers are allowed as the bug number.'
            };

            socorro.ui.setUserMsg('#signature-details', response);
        }
    });
});
