$(document).ready(function(){
    $('.show-all-topcrashers').click(function(){

        var product = $('.product', this).text();
        var icon = $('.icon', this).text();
        var localsOnly = $(this).parent();
        $('.widgetData-' + product + '-full-list', localsOnly).toggle();

        if(icon.indexOf('+') == -1){
	  $('.icon', this).text("[+]");
	} else {
	  $('.icon', this).text("[-]");
	}
      });
        //TODO does autoHeight have a bug?
      $(".topcrashersaccord").accordion({
	header: 'h3',
        autoHeight: false
      });
      //When First widget is small we want the second widget to clear it and 
      //start a new row...
      $( $(".topcrashersaccord").get(0) ).css('margin-bottom', '33px');
});
