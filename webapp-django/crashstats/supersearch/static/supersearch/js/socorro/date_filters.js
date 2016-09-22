/*global $ window moment */

$(function () {
    /**
     * Interface to deal with the date filters in the Search form.
     *
     * Initializes the fields to have a nice date picker UI, then exposes:
     *  - get(key = enum['to', 'from']) -> Date object
     *  - set(key = enum['to', 'from'], value = Date object) -> void
     *  - setDates(dates = Array of strings) -> void
     *  - getDates() -> Array of strings
     */
    window.DateFilters = (function () {
        var filters = {
            from: $('.datetime-picker.date_from').flatpickr(),
            to: $('.datetime-picker.date_to').flatpickr(),
        };

        var setDate = function (key, value) {
            filters[key].setDate(value, true);
        };

        var getDate = function (key) {
            return moment(filters[key].input.value + 'Z').utc().toDate();
        };

        // Limit filters based on the other filter's value.
        filters.to.set('minDate', getDate('from'));
        filters.from.set('maxDate', getDate('to'));

        filters.from.config.onChange = function (dateObj) {
            filters.to.set('minDate', dateObj);
        };
        filters.to.config.onChange = function (dateObj) {
            filters.from.set('maxDate', dateObj);
        };

        // Enable the date filters range shortcuts.
        $('.date-shortcuts').on('click', 'a', function (e) {
            e.preventDefault();

            var range = $(this).data('range');
            var value = parseInt(range.slice(0, -1));
            var unit = range.slice(-1);
            var toDate = moment().utc().toDate();
            var fromDate = moment().utc().subtract(value, unit).toDate();

            setDate('to', toDate);
            setDate('from', fromDate);
        });

        return {
            set: setDate,
            get: getDate,
            setDates: function (dates) {
                // Set date filters values.
                dates.forEach(function (value) {
                    var date;
                    if (value.indexOf('>') === 0) {
                        if (value.indexOf('>=') === 0) {
                            date = value.slice(2);
                        }
                        else {
                            date = value.slice(1);
                        }
                        setDate('from', moment(date).toDate());
                    }
                    else if (value.indexOf('<') === 0) {
                        if (value.indexOf('<=') === 0) {
                            date = value.slice(2);
                        }
                        else {
                            date = value.slice(1);
                        }
                        setDate('to', moment(date).toDate());
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
