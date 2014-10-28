/*global alert:true location:true */
(function ($, document) {
    'use strict';

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function fetch_events() {

        function show_pagination_links(count, batch_size, page) {
            var $pagination = $('.pagination').hide();
            $('.page-wrapper').hide();
            $pagination.find('a').hide();
            var show = false;
            if (count > batch_size) {
                $('.page-wrapper').show();
                // there's more to show possible
                if (batch_size * page < count) {
                    // there is more to show
                    $pagination.find('.next').show();
                    show = true;
                }
                if (batch_size * (page - 1) > 0) {
                    // there is stuff in the past to show
                    $pagination.find('.previous').show();
                    $pagination.show();
                }
            }
            if (show) {
                $pagination.show();
            }
        }

        function tdURLOrEmpty(url) {
            if (url) {
                return $('<td>').append(
                    $('<a>').text('Edit').attr('href', url)
                );
            } else {
                return $('<td>').text('n/a');
            }
        }

        function toggleExpandPre(event) {
            event.preventDefault();
            var self = $(this);
            var parent = self.closest('td');
            var pre = $('pre', parent);
            pre.toggle();
            if (self.text() === 'Expand') {
                self.text('Collapse');
            } else {
                self.text('Expand');
            }
        }

        start_loading();
        var $form = $('#filter');
        var url = $form.data('dataurl');
        var data = $form.serialize();
        $.getJSON(url, data, function(response) {
            stop_loading();
            $('.count b').text(response.count);
            $('.count:hidden').show();
            $('tbody tr', $form).remove();
            var $tbody = $('tbody', $form);
            $('tr', $tbody).remove();
            $.each(response.events, function(i, event) {
                var timestamp = moment(event.timestamp);
                $('<tr>')
                    .append($('<td>').text(event.user))
                    .append($('<td>').text(event.action))
                    .append($('<td>')
                            .text(timestamp.fromNow())
                            .attr('title', timestamp.format('LLLL')))
                    .append(tdURLOrEmpty(event.url))
                    .append($('<td>').append(
                            $('<a href="#">').text('Expand').click(toggleExpandPre))
                        .append(
                            $('<pre>').text(JSON.stringify(event.extra, undefined, 4))
                        ))
                    .appendTo($tbody);
            });
            $('.page').text(response.page);
            show_pagination_links(
                response.count,
                response.batch_size,
                response.page
            );
        });
    }

    function reset_page() {
        $('#filter').find('[name="page"]').val('1');
    }

    $(document).ready(function() {

        var $form = $('#filter');
        $('input.reset', $form).click(function() {
            $form[0].reset();
            reset_page();
            $('.pagination').hide();
            fetch_events();
            return false;
        });

        $form.submit(function() {
            reset_page();
            fetch_events();
            return false;
        });

        reset_page();

        $('.pagination .next').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) + 1);
            $('.pagination').hide();
            fetch_events();
        });

        $('.pagination .previous').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) - 1);
            $('.pagination').hide();
            fetch_events();
        });

        fetch_events();
    });

}($, document));
