$(function() {
    $('button[name="edit"]').click(function() {
        location.href = location.pathname + $(this).val() + '/';
    });
});
