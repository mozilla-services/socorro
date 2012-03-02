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
          if (data.bugs) {
              $.each(data.bugs, function(i, v) {
                bugTable[v.id] = v;
              });
          }
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

    $('.bug_ids_more').hover(function() {
        var inset = 10,
        cell = $(this),
        bugList = cell.find('.bug_ids_expanded_list');

        bugList.css({
            top: cell.position().top - inset,
            left: cell.position().left - (bugList.width() + inset)
        }).toggle();
    });
});
