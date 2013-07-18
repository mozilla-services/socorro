/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(document).ready(function() {
    /* show / hide NOSCRIPT support */
    $('.bug_ids_extra').hide();
    $('.bug_ids_more').show();

    var bugzillaIds = [],
    scrubbedIds = [];
    $('.bug-link').each(function(i, v) {
        bugzillaIds.push(v.innerHTML);
    });
    //remove duplicates from array
    scrubbedIds = jQuery.unique(bugzillaIds);

    var batchSize = 100,
    scrubbedIdsLength = scrubbedIds.length,
    updateBugStatus = function(bugzilla_ids) {
        $.ajax({
            url: "/buginfo/bug?bug_ids=" + bugzilla_ids + "&include_fields=summary,status,id,resolution",
            dataType: 'json',
            success: function(data) {
                var bugTable = {};
                if (data.bugs) {
                    $.each(data.bugs, function(i, v) {
                        if (!("resolution" in v)) {
                            v.resolution = "---";
                        }
                        bugTable[v.id] = v;
                    });
                }

                $('.bug-link').each(function(i, v) {
                    var bug = bugTable[v.innerHTML];
                    if (bug) {
                        $(this).attr("title", bug.status + " " + bug.resolution + " " + bug.summary);

                        if(bug.status.length > 0 &&
                            !(bug.status in {'UNCONFIRMED': 1,'NEW': 1,'ASSIGNED': 1,'REOPENED': 1})) {
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
    };

    if (scrubbedIdsLength) {
        var startIndex = 0,
        endIndex = 1;

        while(startIndex < scrubbedIdsLength) {
            endIndex += batchSize;
            updateBugStatus(scrubbedIds.slice(startIndex, endIndex));
            startIndex = endIndex;
        }
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
