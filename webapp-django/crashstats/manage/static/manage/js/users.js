/*global alert:true location:true PaginationUtils:true */
(function($, document) {
    'use strict';

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function fetch_users() {
        function show_groups(groups) {
            var names = $.map(groups, function(item) {
                return item.name;
            });
            return names.join(', ');
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
            $.each(response.users, function(i, user) {
                $('<tr>')
                    .append($('<td>').text(user.email))
                    .append($('<td>').text(user.is_superuser))
                    .append($('<td>').text(user.is_active))
                    .append($('<td>').text(show_groups(user.groups)))
                    .append($('<td>').text(moment(user.last_login).fromNow()))
                    .append(
                        $('<td>').append(
                            $('<a>')
                                .attr('href', location.pathname + user.id + '/')
                                .text('Edit')
                        )
                    )
                    .appendTo($tbody);
            });
            $('.page').text(response.page);
            PaginationUtils.show_pagination_links(
                response.count,
                response.batch_size,
                response.page
            );
        });
    }

    function reset_page() {
        $('#filter')
            .find('[name="page"]')
            .val('1');
    }

    $(document).ready(function() {
        var $form = $('#filter');
        $('input.reset', $form).click(function() {
            $form[0].reset();
            reset_page();
            $('.pagination').hide();
            fetch_users();
            return false;
        });

        $form.submit(function() {
            reset_page();
            fetch_users();
            return false;
        });

        reset_page();

        $('.pagination .next').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) + 1);
            $('.pagination').hide();
            fetch_users();
        });

        $('.pagination .previous').click(function(e) {
            e.preventDefault();
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val()) - 1);
            $('.pagination').hide();
            fetch_users();
        });

        fetch_users();
    });
})($, document);
