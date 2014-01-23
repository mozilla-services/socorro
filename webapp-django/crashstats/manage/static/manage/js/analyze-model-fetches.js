$(function() {
    $('table.tablesorter').tablesorter();
    $('a.only-urls').click(function() {
        $('.only-filter .selected').removeClass('selected');
        $(this).addClass('selected');
        $('tr.type-classes').hide();
        $('tr.type-urls').show();
        return false;
    });
    $('a.only-classes').click(function() {
        $('.only-filter .selected').removeClass('selected');
        $(this).addClass('selected');
        $('tr.type-urls').hide();
        $('tr.type-classes').show();
        return false;
    });
    $('a.both').click(function() {
        $('.only-filter .selected').removeClass('selected');
        $(this).addClass('selected');
        $('tr.type-classes').show();
        $('tr.type-urls').show();
        return false;
    });
});
