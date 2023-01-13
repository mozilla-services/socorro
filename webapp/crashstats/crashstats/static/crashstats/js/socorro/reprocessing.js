$(function () {
  var parent = $('#reprocess');

  $('form', parent).on('submit', function (event) {
    event.preventDefault();
    var crash_id = parent.data('crash-id');

    // make sure previous result flash messages are hidden
    $('.reprocessing-success', parent).hide();
    $('.reprocessing-error', parent).hide();

    // disable the submit button
    $('form button', parent).prop('disabled', true);

    // show a waiting message
    $('.waiting', parent).show();

    $.post('/api/Reprocessing/', { crash_ids: crash_id })
      .done(function () {
        $('.reprocessing-success', parent).show();
      })
      .fail(function (jqXHR) {
        $('.reprocessing-error .status', parent).text(jqXHR.status);
        $('.reprocessing-error pre', parent).text(jqXHR.responseText);
        $('.reprocessing-error', parent).show();
      })
      .always(function () {
        $('.waiting', parent).hide();
        $('form button', parent).prop('disabled', false);
      });
  });
});
