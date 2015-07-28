/* global Panels, $ */


var Reports = (function() {
    var loaded = false;

    function post_activate($panel) {

        // replace every pagination HREF URL with the partial-url instead
        // but keep the query string part
        var partial_url = $('#reports').data('partial-url');
        $('.pagination a', $panel).each(function() {
            var old_pathname = this.pathname;
            this.pathname = partial_url;
            var href = this.href;
            this.pathname = old_pathname;
            $(this).click(function(event) {
                event.preventDefault();
                Reports.reload(href);
            });
        });

        $('a[href="#reports-form"]', $panel).click(function(event)  {
            event.preventDefault();
            document.getElementById('reports-form').scrollIntoView();
        });

        $wrapper = $('.wrapper', $panel);
        var columns = $wrapper.data('columns');
        var report_list = $('#reports-list');

        // Make sure we have results before we continue
        if (report_list.length > 0 && typeof columns !== 'undefined') {
            // update the select widget
            var $source = $('select[name="available"]', $panel);
            var $destination = $('select[name="chosen"]', $panel);
            $.each(columns.split(','), function(i, value) {
                var $op = $('option[value="' + value + '"]', $source).appendTo($destination);
            });
            $('.visually-hidden', $panel).removeClass('visually-hidden');

            $('a.sort-header', $panel).each(function() {
                $(this).click(function(event) {
                    event.preventDefault();
                    this.pathname = partial_url;
                    Reports.reload(this.href);
                });
            });

            $('th.header', $panel).click(function() {
                $('a.sort-header', this).click();
            });
        }
    }

    return {
       reload: function(url) {
           loaded = false;
           var $panel = $('#reports');
           $('.loading-placeholder', $panel).show();
           $('.inner', $panel).html('');
           $('form', $panel).addClass('visually-hidden');
           $('.reports-form-hint', $panel).addClass('visually-hidden');
           return Reports.activate(url);
       },
       activate: function(url) {
           url = url || null;
           if (loaded) return;
           loaded = true;

           var $panel = $('#reports');
           var deferred = $.Deferred();
           if (!url) {
               url = $panel.data('partial-url');
               var qs = location.href.split('?')[1].split('#')[0];
               url += '?' + qs;
           }
           // do this so that the URL becomes /?c=One&c=Two&c=Three
           if (Columns.value().length) {
               url += '&c=' + Columns.value().join('&c=');
           }
           var req = $.ajax({url: url});
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);

               post_activate($panel);
               deferred.resolve();
           });
           req.fail(function(data, textStatus, errorThrown) {
               $('.loading-placeholder', $panel).hide();
               $('.loading-failed', $panel).show();
               deferred.reject(data, textStatus, errorThrown);
           });

           return deferred.promise();
       }
    };
})();

Panels.register('reports', function() {
    // executed every time the Reports panel is activated
    return Reports.activate();
});


var Columns = (function() {
    var columns = null;
    var key = 'report-list-report-columns';

    return {
        value: function() {
            if (columns === null) {
                columns = JSON.parse(
                    localStorage.getItem(key) || '[]'
                );
            }
            return columns;
        },
        save: function(new_columns, callback) {
            columns = new_columns;
            localStorage.setItem(key, JSON.stringify(columns));
            if (callback) callback();
        }
    };
})();


$(function() {

    // to track if any add or removal is done before pressing Save
    var changes_made = false;

    var $form = $('#reports form');
    $('button[name="add"]', $form).click(function() {
        $('select[name="available"] option:selected', $form).each(function(i, each) {
            $(each).appendTo($('select[name="chosen"]', $form));
            changes_made = true;
        });
        if (changes_made) {
            $('button[name="save"]', $form).removeClass('disabled');
        } else {
            alert('Nothing chosen to move over');
        }
        return false;
    });
    $('button[name="remove"]', $form).click(function() {
        $('select[name="chosen"] option:selected', $form).each(function(i, each) {
            $(each).appendTo($('select[name="available"]', $form));
            changes_made = true;
        });
        if (changes_made) {
            $('button[name="save"]', $form).removeClass('disabled');
        } else {
            alert('Nothing chosen to move back');
        }
        return false;
    });
    $('button[name="save"]', $form).click(function() {
        if (!changes_made) return false;
        var columns = [];
        $('select[name="chosen"] option', $form).each(function(i, each) {
            columns.push(each.value);
        });
        changes_made = false;
        $('button[name="save"]', $form).addClass('disabled');
        Columns.save(columns, function() {
            // Reports.reload() returns a promise but
            // we don't really care when it resolves at this point
            Reports.reload();
        });
        return false;
    });
});
