$(document).ready(function() { 
    /* show / hide NOSCRIPT support */
    $('.bug_ids_extra').hide();
    $('.bug_ids_more').show();

    var query_string = "";
    $('.bug-link').each(function(i, v) {
      query_string += v.innerHTML + ",";
    });
    
    if (query_string) { 
      $.ajax({
        url: "/buginfo/bug?id=" + query_string + "&include_fields=summary,status,id,resolution", 
        dataType: 'json',
        success: function(data) {
          var bugTable = {}; 
          $.each(data.bugs, function(i, v) {
            bugTable[v.id] = v;
          });
          $('.bug-link').each(function(i, v) {
            var bug = bugTable[v.innerHTML];
            if (bug) {
              $(this).attr("title", bug.status + " " + bug.resolution + " " + bug.summary);
              if(bug.resolution.length > 0 && 
                 !(bug.resolution in ['UNCONFIRMED','NEW','ASSIGNED','REOPENED'])) {
                $(this).addClass("strike");
              }
            }
          });
          $('.bug_ids_expanded .bug-link').each(function(i, v) {
            var bug = bugTable[v.innerHTML],
                current;
            if (bug) {
              current = $(this).html();
              $(this).after(" " + bug.status + " " + bug.resolution + " " + bug.summary);
            }
          });
        } 
      });
    }
    
    // Bugzilla Integration
    $('.bug_ids_more').hover(function(){
	var inset = 10,
	    cell = $(this).parents('td'),
	    bugList = cell.find('.bug_ids_expanded_list');
	bugList.show()
          .css({top: cell.position().top - inset,
                 left: cell.position().left - bugList.width() + cell.width() - inset - 3
          })
	  .hover(function(){}, function(){ bugList.hide(); });
        return false;
      }, function(){});
});
