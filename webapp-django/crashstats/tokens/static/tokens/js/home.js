$(function() {

    'use strict';

    $('.token p.code[data-key]').each(function() {
        var p = $(this);
        p.prepend(
            $('<code>')
            .addClass('truncated')
            .text(p.data('key').substr(0, 12) + '…')
        ).prepend(
            $('<code>')
            .addClass('whole')
            .text(p.data('key'))
            .hide()
        );
    });

    $('.token').on('click', 'p.code button', function(event) {
        event.preventDefault();
        var $button = $(this);
        var prev_text = $button.text();
        $button.text($button.data('toggle'));
        $button.data('toggle', prev_text);
        $('code', $button.parents('p.code')).toggle();
    });

    $('form.delete').submit(function() {
        if ($(this).data('expired')) {
            return true;
        } else {
            return confirm('Are you sure you want to delete this API Token?');
        }

    });
});
