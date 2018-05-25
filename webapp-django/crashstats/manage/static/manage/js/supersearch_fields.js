$(function() {
  $('.tablesorter').tablesorter();
  $('.delete').click(function() {
    var field_name = $(this).data('field-name');
    return confirm('Do you really want to delete the "' + field_name + '" field?');
  });
});
