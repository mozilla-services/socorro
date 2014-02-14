function perform_lookup() {
    var vendor_hex = $('#id_vendor_hex').val().trim();
    var adapter_hex = $('#id_adapter_hex').val().trim();
    if (!vendor_hex) {
        alert("Enter a Vendor hex first");
        return;
    }
    if (!adapter_hex) {
        alert("Enter an Adapter hex first");
        return;
    }
    var url = $('form.edit').data('lookup-url');
    $('.lookup-result:visible').hide();
    $.get(url, {vendor_hex: vendor_hex, adapter_hex: adapter_hex})
        .done(function(response) {
            if (response.total) {
                $('#something-found').show();
                var hit = response.hits[0];
                if (!$('#id_vendor_name').val()) {
                    $('#id_vendor_name').val(hit.vendor_name);
                }
                if (!$('#id_adapter_name').val()) {
                    $('#id_adapter_name').val(hit.adapter_name);
                }
            } else {
                $('#nothing-found').show();
            }
        })
        .fail(function() {
            alert('Unable to perform lookup');
        }).always(function() {
            setTimeout(function() {
                $('.lookup-result:visible').hide();
            }, 5 * 1000);
        });
    console.log(vendor_hex, adapter_hex);
}

$(function() {
    // add little alerts for showing about the lookup
    $('<span>')
        .addClass('lookup-result')
        .hide()
        .attr('id', 'nothing-found')
        .text('Nothing found')
        .insertAfter($('#id_adapter_hex'));
    $('<span>')
        .addClass('lookup-result')
        .hide()
        .attr('id', 'something-found')
        .text('Known graphics device found')
        .insertAfter($('#id_adapter_hex'));
    // add a look-up button
    $('<button>')
        .text('Look up')
        .click(function(e) {
            e.preventDefault();
            perform_lookup();
        })
        .insertAfter($('#id_adapter_hex'));
});
