var PaginationUtils = (function() {
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

    return {
        show_pagination_links: show_pagination_links,
    };

})();
