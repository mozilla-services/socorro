/*global alert:true location:true PaginationUtils:true */
(function ($, document) {
    'use strict';

    function humanFileSize(bytes, precision) {
        var units = [
            'bytes',
            'Kb',
            'Mb',
            'Gb',
            'Tb',
            'Pb'
        ];
        if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) {
            return '?';
        }
        var unit = 0;
        while (bytes >= 1024) {
            bytes /= 1024;
            unit++;
        }
        return bytes.toFixed(+precision) + ' ' + units[unit];
    }

    function start_loading() {
        $('.pleasewait').show();
    }

    function stop_loading() {
        $('.pleasewait').hide();
    }

    function fetch_uploads() {

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
            $.each(response.items, function(i, upload) {
                $('<tr>')
                    .append($('<td>').append(
                        $('<a>')
                            .attr('href', upload.user.url)
                            .text(upload.user.email)))
                    .append($('<td>').text(upload.filename))
                    .append($('<td>').append(
                        $('<a>')
                            .attr('href', upload.url)
                            .text('List Content')))
                    .append($('<td>').text(humanFileSize(upload.size)))
                    .append($('<td>').text(moment(upload.created).fromNow()))
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
        $('#filter').find('[name="page"]').val('1');
    }

    $(document).ready(function() {

        var $form = $('#filter');
        $('input.reset', $form).click(function() {
            $form[0].reset();
            reset_page();
            $('.pagination').hide();
            fetch_uploads();
            return false;
        });

        $form.submit(function() {
            reset_page();
            fetch_uploads();
            return false;
        });

        reset_page();

        function updatePage(incr) {
            var $page = $form.find('[name="page"]');
            $page.val(parseInt($page.val())+ incr);
            $('.pagination').hide();
        }

        $('.pagination .next').click(function(e) {
            e.preventDefault();
            updatePage(1);
            fetch_uploads();
        });

        $('.pagination .previous').click(function(e) {
            e.preventDefault();
            updatePage(-1);
            fetch_uploads();
        });

        fetch_uploads();
    });

}($, document));
