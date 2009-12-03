$(document).ready(function() { 
    $('.other_ver form').show();
    $('.no_script_other_ver').remove();
    $("#topcrashers #show")
        .find('a').click(function(e) {
            e.preventDefault();
            $(this).parent().find('a').removeClass('selected');
            $(this).addClass('selected');

            var count = parseInt($(this).text());
            $('.crasher_list table tbody').each(function() {
                $(this).find('tr:lt('+count+')').show();
                $(this).find('tr:gt('+(count-1)+')').hide();
            });
        }).end()
        .find('a:first').click().end()
        .show();
    $('.other_ver select').change(function() {
	var form = $(this).parents('form');
	var product = form.find('input[name=product]').attr('value');
	var version = $(this).val();

        if ($(this).val()) {
	    window.location = form.attr('action') + '/' + product + '/' + version + '/' + 7;
        }
    });
});
