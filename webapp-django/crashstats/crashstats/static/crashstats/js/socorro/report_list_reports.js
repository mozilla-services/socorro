/* global Panels */


var Reports = (function() {
    var loaded = false;

    return {
       reload: function() {
           loaded = false;
           var $panel = $('#reports');
           $('.loading-placeholder', $panel).show();
           $('.inner', $panel).html('');
           $('form', $panel).addClass('visually-hidden');
           $('.reports-form-hint', $panel).addClass('visually-hidden');
           return Reports.activate();
       },
       activate: function() {
           if (loaded) return;
           if (Columns.value() === null) {
               // the storage hasn't returned yet!
               return Columns.load(Reports.activate);
           }
           loaded = true;

           var $panel = $('#reports');
           var deferred = $.Deferred();
           var url = $panel.data('partial-url');
           var qs = location.href.split('?')[1].split('#')[0];
           url += '?' + qs;
           // do this so that the URL becomes /?c=One&c=Two&c=Three
           if (Columns.value().length) {
               url += '&c=' + Columns.value().join('&c=');
           }
           var req = $.ajax({url: url});
           req.done(function(response) {
               $('.loading-placeholder', $panel).hide();
               $('.inner', $panel).html(response);

               // update the select widget
               $wrapper = $('.wrapper', $panel);
               var columns = $wrapper.data('columns');
               var $source = $('select[name="available"]', $panel);
               var $destination = $('select[name="chosen"]', $panel);
               $.each(columns.split(','), function(i, value) {
                   var $op = $('option[value="' + value + '"]', $source).appendTo($destination);
               });
               $('.visually-hidden', $panel).removeClass('visually-hidden');
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
    var COLUMNS = null;
    var KEY = 'report-list-report-columns';

    // New API, new object || Where the polyfill lives
    var storage = navigator.storage || navigator.alsPolyfillStorage;

    return {
        value: function() {
            return COLUMNS;
        },
        load: function(callback) {
           storage
               .get(KEY)
               .then(function(value) {
                   if (value) {
                       COLUMNS = value.split(',');
                   } else {
                       // happens when you've never saved this before
                       COLUMNS = [];
                   }
                   if (callback) callback();
               }, function(e) {
                   console.log('Unable to retrieve columns', e);
                   if (callback) callback();
               });
        },
        save: function(columns, callback) {
            COLUMNS = columns;
            storage
                .set(KEY, columns.join(','))
                .then(function() {
                    if (callback) callback();
                }, function(e) {
                    console.log('Unable to save columns', e);
                    if (callback) callback();
                });
        }
    };
})();


// we can try to run this as soon as possible
// so it's done when Reports.activate() gets called
Columns.load();


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
