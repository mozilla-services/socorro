/* global moment */

$(function() {
    $('time.ago').each(function() {
        var self = $(this);
        self
          .attr('title', self.text())
          .text(moment(self.data('date')).fromNow());
    });

    $('time.in').each(function() {
        var self = $(this);
        self
          .attr('title', self.text())
          .text(moment(self.data('date')).fromNow(true));
    });

});
