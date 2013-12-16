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
});
