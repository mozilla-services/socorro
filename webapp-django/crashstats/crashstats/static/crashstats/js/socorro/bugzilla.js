/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// from https://github.com/janl/mustache.js/blob/master/mustache.js#L82
var entityMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': '&quot;',
    "'": '&#39;',
    "/": '&#x2F;'
};
function escapeHtml(string) {
    return String(string).replace(/[&<>"'\/]/g, function (s) {
        return entityMap[s];
    });
}

var Bugzilla = (function() {
    var NOT_DONE_STATUSES = ['UNCONFIRMED', 'NEW', 'ASSIGNED', 'REOPENED'];
    var URL = '/buginfo/bug';  // TODO move this outside

    function fetch_remotely(bug_ids) {
        var deferred = $.Deferred();
        var data = {bug_ids: bug_ids.join(','), include_fields: 'summary,status,id,resolution'};
        var req = $.getJSON(URL, data);
        req.done(function(response) {
            var table = {};
            $.each(response.bugs, function(i, each) {
                table[each.id] = each;
            });
            var fetched_bug_ids = [];
            $('.bug-link-without-data').each(function() {
                // we only fetched some bugs into `table` so
                // we might not have data on this one yet
                var $link = $(this);
                if ($link.data('id') in table) {
                    $link
                        .removeClass('bug-link-without-data')
                        .addClass('bug-link-with-data');
                    var data = table[$link.data('id')];
                    $link.data('summary', data.summary);
                    $link.data('resolution', data.resolution);
                    $link.data('status', data.status);
                    fetched_bug_ids.push($link.data('id'));
                }
            });
            deferred.resolve($.unique(fetched_bug_ids));
        });
        req.fail(function(data, textStatus, errorThrown) {
            deferred.reject();
        });
        return deferred.promise();
    }

    function fetch(bug_ids) {
        var batch_size = 100;
        var i = 0, j = 0;
        while (i < bug_ids.length) {
            j += batch_size;
            // For each batch, do an XHR on the data
            // which also appends that fetched data to each link tag.
            // When the data has been downloaded and attached to
            // each link tag run this to update
            fetch_remotely(bug_ids.slice(i, j))
              .done(Bugzilla.transform_with_data);
            i = j;
        }
    }

    return {
        transform_with_data: function() {
            // this function is potentially called repeated every time
            // fetch_without_data() has fetched more data for the links
            $('.bug-link-with-data').each(function() {
                var $link = $(this);
                if ($link.data('transformed')) return;  // already done
                var status = $link.data('status');
                var resolution = $link.data('resolution') || '---';
                var summary = $link.data('summary');

                var combined = status + ' ' + resolution + ' ' + summary;
                $link.attr('title', escapeHtml(combined));
                if ($link.parents('.bug_ids_expanded_list').length) {
                    $link.after(' ' + escapeHtml(combined));
                }
                if (status && $.inArray(status, NOT_DONE_STATUSES) === -1) {
                    $link.addClass("strike");
                }
                $link.data('transformed', true);
            });
        },
        fetch_without_data: function() {
            // in batches, do a XHR to pull down more details about bugs
            // for those bug links that don't have data yet
            var unique_bug_ids = [];
            $('.bug-link-without-data').each(function() {
                unique_bug_ids.push($(this).data('id'));
            });
            unique_bug_ids = $.unique(unique_bug_ids);
            if (unique_bug_ids.length) {
                fetch(unique_bug_ids);
            }
        }
    };
})();


$(function() {
    // apply to all bug links that already have the data
    // when the template was rendered
    Bugzilla.transform_with_data();
    // XHR fetch all other ones
    Bugzilla.fetch_without_data();

    $('.bug_ids_more').hover(function() {
        if (!$('.bug-link', this).length) return;
        var inset = 10;
        var $cell = $(this);
        var bugList = $cell.find('.bug_ids_expanded_list');
        bugList.css({
            top: $cell.position().top - inset,
            left: $cell.position().left - (bugList.width() + inset)
        }).toggle();
    });

});
