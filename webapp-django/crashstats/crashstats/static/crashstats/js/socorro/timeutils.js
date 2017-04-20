/* global moment */

$(function() {
    function replaceTimeTag(inTheFuture) {
        return function () {
            var self = $(this);
            var date = self.attr('datetime') || self.data('date');
            self.attr('title', self.text())
                .text(moment(date).fromNow(inTheFuture));
        };
    }

    function updateTimes() {
        $('time-tag.ago').each(replaceTimeTag(false));
        $('time-tag.in').each(replaceTimeTag(true));
    }
    updateTimes();
    setInterval(updateTimes, 60 * 1000);
});
