import { default as moment } from 'moment';

$(function () {
  /**
   * Interface to deal with the date filters in the Search form.
   *
   * Initializes the fields to have a nice date picker UI, then exposes:
   *  - getDate(key = enum['to', 'from']) -> Date object
   *  - setDate(key = enum['to', 'from'], value = Date object) -> void
   *  - setDates(dates = Array of strings) -> void
   *  - getDates() -> Array of strings
   */
  window.DateFilters = (function () {
    var filters = {
      fromDate: $('.date-filters > div.date-from > input[type="date"]'),
      fromTime: $('.date-filters > div.date-from > input[type="time"]'),
      toDate: $('.date-filters > div.date-to > input[type="date"]'),
      toTime: $('.date-filters > div.date-to > input[type="time"]'),
    };

    function setDate(key, value) {
      value = moment(value).utc();
      filters[key + 'Date'].val(value.format('YYYY-MM-DD'));
      filters[key + 'Time'].val(value.format('HH:mm'));
    }

    function getDate(key) {
      // Take the date and time values and mush them together into a string for
      // easier conversion
      var d = filters[key + 'Date'].val() + 'T' + filters[key + 'Time'].val() + 'Z';
      return moment(d).utc().toDate();
    }

    function removeSelectedShortcut() {
      $('.date-shortcuts a').removeClass('selected');
    }

    // Enable the date filters range shortcuts.
    $('.date-shortcuts').on('click', 'a', function (e) {
      e.preventDefault();
      var thisElt = $(this);

      var range = thisElt.data('range');
      var toDate, fromDate;

      if (range === 'dayends') {
        // "dayends" takes the dates and moves the "from" date to the beginning
        // of the day and the "to" date to the end of the day
        fromDate = getDate('from');
        fromDate.setUTCHours(0);
        fromDate.setUTCMinutes(0);
        fromDate.setUTCSeconds(0);
        setDate('from', fromDate);

        toDate = getDate('to');
        toDate.setUTCHours(23);
        toDate.setUTCMinutes(59);
        toDate.setUTCSeconds(59);
        setDate('to', toDate);

        return;
      }

      var value = parseInt(range.slice(0, -1));
      var unit = range.slice(-1);

      // Start with "now" which is a Javascript Date object in the local
      // timezone, convert to utc, and then converts to a Date.
      var now = new Date();
      toDate = moment(now).utc().toDate();
      fromDate = moment(now).utc().subtract(value, unit).toDate();

      setDate('to', toDate);
      setDate('from', fromDate);

      // Update the selected shortcut
      removeSelectedShortcut();
      thisElt.addClass('selected');
    });

    return {
      set: setDate,
      get: getDate,
      setDates: function (dates) {
        // Remove any previously selected date shortcut because it
        // will most likely be wrong now.
        $('.date-shortcuts a').removeClass('selected');

        if (!Array.isArray(dates)) {
          dates = [dates];
        }

        // Set date filters values.
        dates.forEach(function (value) {
          var date;
          if (value.indexOf('>') === 0) {
            if (value.indexOf('>=') === 0) {
              date = value.slice(2);
            } else {
              date = value.slice(1);
            }
            setDate('from', moment.utc(date).utcOffset(date).toDate());
          } else if (value.indexOf('<') === 0) {
            if (value.indexOf('<=') === 0) {
              date = value.slice(2);
            } else {
              date = value.slice(1);
            }
            setDate('to', moment.utc(date).utcOffset(date).toDate());
          }
        });
      },
      getDates: function () {
        var dateFrom = getDate('from');
        var dateTo = getDate('to');
        var dates = [];
        if (dateFrom) {
          dates.push('>=' + dateFrom.toISOString());
        }
        if (dateTo) {
          dates.push('<' + dateTo.toISOString());
        }
        return dates;
      },
    };
  })();
});
