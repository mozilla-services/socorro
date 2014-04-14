$(function() {
    $('p.code button').click(function(event) {
        event.preventDefault();
        var $button = $(this);
        var prev_text = $button.text();
        $button.text($button.data('toggle'));
        $button.data('toggle', prev_text);

        var $parent = $button.parents('p.code');
        $('.rest-hidden', $parent).toggle();
        $('.rest-cover', $parent).toggle();
    });

    $('form.delete').submit(function() {
        return confirm('Are you sure you want to delete this API Token?');
    });
});
