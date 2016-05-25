$(function() {
    var parent = $('#reprocess');

    $('form', parent).on('submit', function(event) {
        event.preventDefault();
        var crash_id = parent.data('crash-id');

        // make sure previous result flash messages are hidden
        $('.reprocessing-success', parent).hide();
        $('.reprocessing-error', parent).hide();

        // disable the submit button
        $('form button', parent).prop('disabled', true);

        // show a waiting message
        $('.waiting', parent).show();

        $.post('/api/Reprocessing/', {crash_ids: crash_id})
        .done(function(response) {
            $('.reprocessing-success', parent).show();
        })
        .error(function(jqXHR, textStatus, errorThrown) {
            $('.reprocessing-error .status', parent).text(jqXHR.status);
            $('.reprocessing-error pre', parent).text(jqXHR.responseText);
            $('.reprocessing-error', parent).show();
        })
        .complete(function() {
            $('.waiting', parent).hide();
            $('form button', parent).prop('disabled', false);
        });
    });

    $('.reprocessing-success a', parent).on('click', function(event) {
        event.preventDefault();
        document.location.reload(true);
    });
});
