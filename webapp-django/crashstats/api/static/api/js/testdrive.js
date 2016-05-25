(function ($, document) {
    'use strict';

    var _submission_locked = false;

    $.fn.serializeExclusive = function() {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function() {
            var value;
            if (o[this.name] !== undefined) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                if (this.value)
                  o[this.name].push(this.value || '');
            } else {
                if (this.value)
                  o[this.name] = this.value || '';
            }
        });
        return o;
    };

    function one_more(element) {
        var container = $(element).parents('td');
        var previous = $('input', container).eq(-1);
        var clone = previous.clone();
        clone.val('');
        clone.insertAfter(previous);
        if ($('input', container).length > 1) {
            $('a.collapse-list', container).css('display', 'inline');
        }
    }

    function one_less(element) {
        var container = $(element).parents('td');
        var last = $('input', container).eq(-1);
        last.remove();
        if ($('input', container).length < 2) {
            $('a.collapse-list', container).css('display', 'none');
        }
    }

    function validate_form(form) {

        function is_int(x) {
            var y = parseInt(x, 10);
            if (isNaN(y)) return false;
            return x==y && x.toString() == y.toString();
        }
        var all_valid = true;
        $('input', form).each(function() {
            var valid = true;
            var element = $(this);
            var value = element.val();
            if (element.hasClass('required') && !value) {
                valid = false;
            } else if (element.hasClass('required') && element.hasClass('validate-int') && !is_int(value)) {
                valid = false;
            } else {
                // we can do more validation but let's not go too crazy yet
            }
            if (!valid) {
                all_valid = false;
                element.addClass('error');
            } else {
                element.removeClass('error');
            }
        });
        return all_valid;
    }

    function submit_form(form) {
        var url = $('p.url code', form).text();

        // Not entirely sure why this is a list
        var method = form.data('methods')[0];
        var ajax_url;
        if (method === 'POST') {
            ajax_url = url;
        } else {
            // unlike regular, form.serialize() by doing it this way we get a
            // query string that only contains actual values
            // The second parameter (`true`) is so that things like
            // `{products: ["Firefox", "Thunderbird"]}`
            // becomes: `products=Firefox&products=Thunderbird`
            var qs = Qs.stringify(form.serializeExclusive(), { indices: false });
            if (qs) {
                url += '?' + qs;
            }
            ajax_url = url;
            if (ajax_url.search(/\?/) == -1) {
                ajax_url += '?';
            } else {
                ajax_url += '&';
            }
            ajax_url += 'pretty=print';
        }

        $('img.loading-ajax', form).show();
        $('button.close', form).hide();

        var container = $('.test-drive', form);
        $.ajax({
           url: ajax_url,
           method: method,
           // Only send the `data` if it's a POST. For get the params are
           // in the `ajax_url` already.
           data: method === 'POST' ? form.serializeArray() : null,
           dataType: 'text',
           success: function(response, textStatus, jqXHR) {
               $('pre', container).text(response);
               $('.status code', container).hide();
               $('.status-error', container).hide();
               $('.response-size code', container).text(filesize(response.length));
               $('.response-size').show();
           },
           error: function(jqXHR, textStatus, errorThrown) {
               $('pre', container).text(jqXHR.responseText);
               $('.status code', container).text(jqXHR.status).show();
               $('.status-error', container).show();
               $('.response-size').hide();
               // in case it was binary before this run
               $('pre', container).show();
               $('.binary-response-warning', container).hide();
           },
           complete: function(jqXHR, textStatus) {
               $('.used-url code', container).text(url);
               $('.used-url a', container).attr('href', url);
               if (method === 'POST') {
                   $('.used-data code')
                   .text(JSON.stringify(form.serializeExclusive()));
                   $('.used-data').show();
               } else {
                   $('.used-data').hide();
               }
               if (jqXHR.getResponseHeader('Content-Type') === 'application/octet-stream') {
                    $('pre', container).hide();
                    $('.binary-response-warning', container).show();
               } else {
                    // in case it was binary *before* this run, reset it
                    $('pre', container).show();
                    $('.binary-response-warning', container).hide();
               }
               container.show();
               setTimeout(function() {
                   // add a slight delay so it feels smoother for endpoints
                   // that complete in milliseconds
                   $('img.loading-ajax', form).hide();
                   $('button.close', form).show();
               }, 500);
               _submission_locked = false;
           }
        });
    }

    $(document).ready(function () {
        $('input.validate-list').each(function() {
            $('<a href="#">-</a>')
              .hide()
              .addClass('collapse-list')
              .attr('title', 'Click to remove the last added input field')
              .click(function(e) {
                  e.preventDefault();
                  one_less(this);
              })
              .insertAfter($(this));
            $('<a href="#">+</a>')
              .addClass('expand-list')
              .attr('title', 'Click to create another input field')
              .click(function(e) {
                  e.preventDefault();
                  one_more(this);
              })
              .insertAfter($(this));
        });

        $('form.testdrive').submit(function(event) {
            var $form = $(this);
            event.preventDefault();
            if (_submission_locked) {
                alert('Currently processing an existing query. Please be patient.');
            } else {
                _submission_locked = true;
                if (validate_form($form)) {
                    submit_form($form);
                } else {
                    _submission_locked = false;
                }
            }
        });

        $('input.error').on('change', function() {
            $(this).removeClass('error');
        });

        $('button.close').on('click', function(event) {
            event.preventDefault();
            $('.test-drive', $(this).parents('form')).hide();
            $(this).hide();
        });

        $('.binary-response-warning').on('click', 'a.show', function(event) {
            event.preventDefault();
            var parent = $(this).closest('.test-drive');
            $('pre', parent).show();
            $(this).hide();
        });

        $('.binary-response-warning').on('click', 'a.open', function(event) {
            event.preventDefault();
            var parent = $(this).closest('.test-drive');
            var url = $('.used-url a', parent).attr('href');
            location.href = url;
            // window.open(url);
        });

    });


}($, document));
