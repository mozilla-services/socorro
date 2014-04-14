/*global alert:true location:true */
(function ($, document) {
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
                    .append($('<td>')
                            .append($('<a>')
                                    .attr('href', location.pathname + user.id + '/')
                                    .text('Edit')))
                    .appendTo($tbody);
            });
        });
    }

    $(document).ready(function() {

        var $form = $('#filter');
        $('input.reset', $form).click(function() {
            $form[0].reset();
            fetch_users();
            return false;
        });

        $form.submit(function() {
            fetch_users();
            return false;
        });

        fetch_users();
    });

}($, document));
