/*global alert:true location:true PaginationUtils:true */
(function ($, document) {
    'use strict';

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function fetch() {

        function deleteToken(button) {
            var id = button.data('id');
            var row = button.parents('tr');
            if (confirm("Are you sure you want to delete this?")) {
                button.text('Deleting');
                var form = $('form#tokens');
                var data = {
                    id: id,
                    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                };
                $.post(form.data('delete-url'), data)
                .then(function(response) {
                    row.fadeOut(300, function() {
                        row.remove();
                    });
                })
                .fail(function() {
                    console.warn('Unable to delete the token');
                    console.error(arguments);
                    $(this).text('Delete');
                });
            }
        }

        function displayKey(value, length) {
            /* return a new jQuery HTML node */
            length = length || 20;
            return $('<code>')
                .addClass('redacted')
                .click(function() {
                    var self = $(this);
                    var current = self.text();
                    var key = self.data('key');
                    if (current !== key) {
                        self.text(key);
                        setTimeout(function() {
                            self.text(key.substr(0, length) + '...');
                        }, 5 * 1000);
                    }
                    return false;
                })
                .text(value.substr(0, length) + '...')
                .data('key', value)
                .attr('title', 'Click to see the whole thing');
        }

        function displayNotes(text, max_length) {
            /* return a new jQuery HTML node */
            max_length = max_length || 100;
            var brief = text;
            if (brief.length > max_length) {
                brief = brief.substr(0, max_length);
                return $('<span>').addClass('redacted').append(
                    $('<span>').addClass('_brief').text(brief + '...')
                    .click(function() {
                        var parent = $(this).parent('span');
                        $('._full', parent).show();
                        $(this).hide();
                    })
                ).append(
                    $('<span>').addClass('_full').hide().html(
                        text.replace('<', '&lt;')
                            .replace('>', '&gt;')
                            .replace('\n', '<br>')
                    )
                    .click(function() {
                        var parent = $(this).parent('span');
                        $('._brief', parent).show();
                        $(this).hide();
                    })
                );
            } else {
                return $('<span>').text(text);
            }

        }

        start_loading();
        var $form = $('#tokens');
        var url = $form.data('data-url');
        var data = $form.serialize();
        $.getJSON(url, data, function(response) {
            stop_loading();
            $('.count b').text(response.count);
            $('.count:hidden').show();
            $('tbody tr', $form).remove();
            var $tbody = $('tbody', $form);
            $('tr', $tbody).remove();
            $.each(response.tokens, function(i, token) {

                var timestamp_text, timestamp = moment(token.expires);
                if (token.expired) {
                    timestamp_text = timestamp.fromNow(false);
                } else {
                    timestamp_text = timestamp.fromNow(true);
                }
                $('<tr>')
                    .append($('<td>').text(token.user))
                    .append($('<td>').append(displayKey(token.key)))
                    .append($('<td>')
                            .text(timestamp_text)
                            .addClass(token.expired ? 'expired' : '')
                            .attr('title', timestamp.format('LLLL')))
                    .append($('<td>')
                            .html(token.permissions.join('<br>')))
                    .append($('<td>')
                            .addClass('notes')
                            .append(displayNotes(token.notes)))
                    .append($('<td>')
                            .append($('<button>')
                                    .text('Delete')
                                    .data('id', token.id)
                                    .click(function(event) {
                                        event.preventDefault();
                                        deleteToken($(this));
                                    })))
                    .appendTo($tbody);
            });
            $('.page').text(response.page);
            PaginationUtils.show_pagination_links(
                response.count,
                response.batch_size,
                response.page
            );

            // If there was a validation error or something in the create
            // form, we don't want the user to miss that and the ajax
            // loaded table data might have obscured the form to be
            // after some vertical scrolling. If so, scroll down.
            if ($('form#create .errorlist').length) {
                $('form#create')[0].scrollIntoView();
            }

        });
    }  // end of function fetch()

    function reset_page() {
        $('#tokens').find('[name="page"]').val('1');
    }

    $(document).ready(function() {

        var $form = $('#tokens');
        $('input.reset', $form).click(function() {
            $form[0].reset();
            reset_page();
            $('.pagination').hide();
            fetch();
            return false;
        });

        $form.submit(function() {
            reset_page();
            fetch();
            return false;
        });

        reset_page();

        $('.pagination .next').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) + 1);
            $('.pagination').hide();
            fetch();
        });

        $('.pagination .previous').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) - 1);
            $('.pagination').hide();
            fetch();
        });

        fetch();

    });

}($, document));
