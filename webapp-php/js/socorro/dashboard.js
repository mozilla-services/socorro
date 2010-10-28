$(document).ready(function(){
    $('#click_up').click(function(){
        $('#click_down').removeClass('selected');
        $('#click_up').addClass('selected');
        $('#top_changers_down').hide()
        $('#top_changers_up').show('fast');
    });

    $('#click_down').click(function(){
        $('#click_up').removeClass('selected');
        $('#click_down').addClass('selected');
        $('#top_changers_up').hide();
        $('#top_changers_down').show('fast');
    });
});
