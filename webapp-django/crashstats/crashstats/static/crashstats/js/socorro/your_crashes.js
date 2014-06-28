$(function () {
    $('.crashes_list time').each(function (i) {
        var elt = $(this);
        var datetime = moment(elt.attr('datetime')).utc().format('MMMM Do YYYY, hh:mm:ss');
        elt.attr('title', datetime);
        elt.text(moment(elt.text()).fromNow());
    });
});
