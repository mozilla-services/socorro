/*global alert:true location:true */
(function ($, document) {
    'use strict';

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function fetch_users(q) {
        function show_groups(groups) {
            var names = $.map(groups, function(item) {
                return item.name;
            });
            return names.join(', ');
        }

        start_loading();
        var url = $('.filter').data('dataurl');
        var data = $('form.filter').serialize();
        $.getJSON(url, data, function(response) {
            stop_loading();
            $('.count b').text(response.count);
            $('.count:hidden').show();
            $('.filter tbody tr').remove();
            var $tbody = $('.filter tbody');
            $('tr', $tbody).remove();
            $.each(response.users, function(i, user) {
                $('<tr>')
                    .append($('<td>').text(user.email))
                    .append($('<td>').text(user.is_superuser))
                    .append($('<td>').text(user.is_active))
                    .append($('<td>').text(show_groups(user.groups)))
                    .append($('<td>')
                            .append($('<a>')
                                    .attr('href', location.pathname + user.id + '/')
                                    .text('Edit')))
                    .appendTo($tbody);
            });
        });
    }

    $(document).ready(function() {

        $('form.filter input.reset').click(function() {
            $('form.filter')[0].reset();
            fetch_users();
            return false;
        });

        $('form.filter').submit(function() {
            fetch_users();
            return false;
        });

        fetch_users();
    });

}($, document));
