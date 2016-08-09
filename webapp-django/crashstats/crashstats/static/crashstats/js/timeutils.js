/* global moment */

$(function() {
    $('time.ago').each(function() {
        var self = $(this);
        var date = self.attr('datetime') || self.data('date');
        self
          .attr('title', self.text())
          .text(moment(date).fromNow());
    });

    $('time.in').each(function() {
        var self = $(this);
        var date = self.attr('datetime') || self.data('date');
        self
          .attr('title', self.text())
          .text(moment(date).fromNow(true));
    });

});
