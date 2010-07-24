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
    
    $("#click_top_crashers").bind("click", function(){
        showHideTop("top_crashers");
    });

    $("#click_top_changers").bind("click", function(){
        showHideTop("top_changers");
    });
});

function showHideTop(id) {
    $("#top_crashers").hide();
    $("#top_changers").hide();
    $("#"+id).show("fast");	
    
    $('#click_top_crashers').removeClass('selected');
    $('#click_top_changers').removeClass('selected');
    $("#click_"+id).addClass('selected');
}