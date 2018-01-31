/*global MG: true, socorro: true */

$(function () {
    'use strict';

    // A polyfill for `endsWith`
    if (!String.prototype.endsWith) {
        String.prototype.endsWith = function(searchString, position) {
            var subjectString = this.toString();
            if (typeof position !== 'number' || !isFinite(position) || Math.floor(position) !== position || position > subjectString.length) {
                position = subjectString.length;
            }
            position -= searchString.length;
            var lastIndex = subjectString.indexOf(searchString, position);
            return lastIndex !== -1 && lastIndex === position;
        };
    }

    // Get the date of the first day of a specified year and week.
    // Source: https://stackoverflow.com/a/16591175
    function getDateOfISOWeek(y, w) {
        var simple = new Date(Date.UTC(y, 0, 1 + (w - 1) * 7));
        var dow = simple.getDay();
        var ISOweekStart = simple;
        if (dow <= 4)
            ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
        else
            ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
        return ISOweekStart;
    }

    var COLORS = ['#6a3d9a', '#e31a1c', '#008800', '#1f78b4'];

    var datapanel = $('#homepage-data-panel');

    var product = datapanel.data('product');
    var versions = datapanel.data('versions');

    // Versions ending in -b are "magic" versions that will be split into all
    // of the beta versions starting with that same version number.
    var betaVersions = [];
    versions.forEach(function (version) {
        if (version.endsWith('b')) {
            betaVersions.push(version);
        }
    });

    // Create date variables. They will be assigned a value in `updateDates()`.
    var endDate;
    var startDate;

    /**
     * Return a string with only the date part of a Date object, in ISO format.
     */
    function dateIsoFormat(date) {
        return date.toISOString().substring(0, 10);
    }

    // Apply colors to version headers
    $('#release_channels h4').each(function (index) {
        $(this).css('color', COLORS[index]);
    });
});
