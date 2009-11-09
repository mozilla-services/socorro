$(document).ready(function() { 
    /* show / hide NOSCRIPT support */
    $('.bug_ids_extra').hide();
    $('.bug_ids_more').show();

    // Bugzilla Integration
    $('.bug_ids_more').hover(function(){
	var inset = 10;
	var cell = $(this).parents('td');
	var bugList = cell.find('.bug_ids_expanded_list');
	bugList.show()
          .css( {top: cell.position().top - inset, left: cell.position().left - bugList.width() + cell.width() - inset - 3 })
	  .hover(function(){}, function(){ bugList.hide(); });
        return false;
      }, function(){});

});