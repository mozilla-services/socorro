$(document).ready(function() {
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
});
