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

    var container = $('#homepage-graph-container');
    var superSearchApiUrl = container.data('supersearch-api');
    var productBuildTypesApiUrl = container.data('product-build-types-api');
    var adiApiUrl = container.data('adi-api');

    var product = container.data('product');
    var versions = container.data('versions');
    var platforms = container.data('platforms');
    var duration = container.data('duration');
    var esShardsPerIndex = container.data('es-shards-per-index');

    var pageTitle = $('title').text();

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

    /**
     * History change handler. Reloads the graph's data.
     */
    window.onpopstate = function (e) {
        duration = e.state.duration;

        $('#duration .selected').removeClass('selected');
        $('#duration .days-' + duration).addClass('selected');

        updateDates();
        loadData();
    };

    /**
     * Click event handler for the duration menu. Changes the history and
     * reloads the graph's data.
     */
    $('#duration').on('click', 'a', function (e) {
        e.preventDefault();

        var link = $(this);

        // Do nothing if this is already selected.
        if (link.hasClass('selected')) {
            return;
        }

        duration = link.data('duration');
        var url = link.attr('href');

        $('#duration .selected').removeClass('selected');
        link.addClass('selected');

        window.history.pushState({ duration: duration }, pageTitle, url);

        updateDates();
        loadData();
    });

    /**
     * Change the dates of the request depending on the duration.
     */
    function updateDates() {
        var ONE_DAY = 24 * 60 * 60 * 1000;  // One day in milliseconds.
        endDate = new Date(Date.now() - ONE_DAY);  // We start with yesterday.
        startDate = new Date(+endDate - (duration * ONE_DAY));
    }

    /**
     * Get count of crashes per day and per version.
     */
    function querySuperSearch() {
        var deferred = $.Deferred();

        // Super Search uses datetimes instead of dates, and thus cannot
        // use yesterday's date as the upper bound. It needs to use today's
        // date so that results from yesterday are returned.
        var searchEndDate = new Date();

        var params = {
            product: product,
            version: versions,
            date: [
                '>=' + dateIsoFormat(startDate),
                '<' + dateIsoFormat(searchEndDate),
            ],
            '_histogram.date': 'version',
            _results_number: 0,
        };

        var url = superSearchApiUrl + '?' + Qs.stringify(params, { indices: false });
        $.ajax({url: url})
        .then(onSuperSearchData)
        .done(function (data) {
            return deferred.resolve(data);
        })
        .fail(onQueryError)
        .fail(function () {
            deferred.reject();
        });

        return deferred;
    }

    /**
     * Get count of average daily installs per day and per version.
     */
    function queryADI() {
        var deferred = $.Deferred();

        var params = {
            product: product,
            versions: versions,
            platforms: platforms,
            start_date: dateIsoFormat(startDate),
            end_date: dateIsoFormat(endDate),
        };

        var url = adiApiUrl + '?' + Qs.stringify(params, { indices: false });
        $.ajax({url: url})
        .then(onADIData)
        .done(function (data) {
            return deferred.resolve(data);
        })
        .fail(onQueryError)
        .fail(function () {
            deferred.reject();
        });

        return deferred;
    }

    // It's useless to query the build types every time. We can cache it
    // the first time and then just return that cached value.
    var buildTypesCache = null;

    /**
     * Get throttle value per build type.
     */
    function queryBuildTypes() {
        var deferred = $.Deferred();

        if (buildTypesCache) {
            return deferred.resolve(buildTypesCache);
        }

        var params = {
            product: product,
        };

        var url = productBuildTypesApiUrl + '?' + Qs.stringify(params, { indices: false });
        $.ajax({url: url})
        .then(onBuildTypesData)
        .done(function (data) {
            // Cache the results.
            buildTypesCache = data;
            return deferred.resolve(data);
        })
        .fail(onQueryError)
        .fail(function () {
            deferred.reject();
        });

        return deferred;
    }

    /**
     * Format data received from SuperSearch to make it simpler and closer to
     * what we will pass to the graph library.
     */
    function onSuperSearchData(data) {
        // If there are shards errors, show a warning to the user that the
        // data is incorrect.
        if (data.errors && data.errors.length) {
            showShardsErrors(data.errors);
        }

        // dataStruct is a temporary data structure that makes it easy to
        // add up crash counts and handle the special cases of beta versions.
        var dataStruct = {};

        // First initialize the structure with all versions and all expected
        // days, each having a crash count of zero.
        // dataStruct becomes something like this:
        // { '2.0': { '2000-01-01': 0, '2000-01-02': 0 } }
        versions.forEach(function (version) {
            dataStruct[version] = {};

            var currentDay = +startDate;
            while (currentDay <= +endDate) {
                var day = dateIsoFormat(new Date(currentDay));
                dataStruct[version][day] = 0;
                currentDay += 24 * 60 * 60 * 1000;
            }
        });

        var dates = data.facets.histogram_date;

        // Now for each day in the results and for each version, we will add
        // the number of crashes to the previously created structure.
        dates.forEach(function (date) {
            var versionsCounts = date.facets.version;

            versionsCounts.forEach(function (versionCount) {
                var version = versionCount.term;
                var versionIndex = versions.indexOf(version);

                var baseVersion = null;

                // If we can find that version number in the requested list
                // of version, that's easy, we just use that.
                if (versionIndex > -1) {
                    baseVersion = version;
                }
                // However if the version was not in the requested versions,
                // that means it's a beta version that should be merged into
                // the results of that beta version's requested version.
                // For example, if we requested results for '2.0b', we might
                // receive results for versions like '2.0b1' and '2.0b99'.
                // All of those results must be summed under the '2.0b' key.
                else if (versionIndex === -1) {
                    betaVersions.forEach(function (betaVersion) {
                        if (version.indexOf(betaVersion) > -1) {
                            baseVersion = betaVersion;
                        }
                    });
                }

                // Now that we know what the requested version was, we can
                // add up the crash count.
                dataStruct[baseVersion][date.term.substring(0, 10)] += versionCount.count;
            });
        });

        // Now transform that data into a format that corresponds to what
        // the graph library will be expecting.
        return transformSuperSearchData(dataStruct);
    }

    /**
     * Format the temporary data structure built from SuperSearch results
     * so that it matches what the graph library expects.
     */
    function transformSuperSearchData(dataStruct) {
        var superSearchData = [];
        versions.forEach(function (version, i) {
            superSearchData[i] = [];
        });

        for (var version in dataStruct) {
            var versionIndex = versions.indexOf(version);

            for (var date in dataStruct[version]) {
                superSearchData[versionIndex].push({
                    date: new Date(date),
                    count: dataStruct[version][date],
                });
            }
        }

        return superSearchData;
    }

    /**
     * Format data received from ADI to make it easier to exploit.
     */
    function onADIData(data) {
        if (data.total === 0) {
            return null;
        }

        var adiData = {};
        for (var i = 0, ln = data.hits.length; i < ln; i++) {
            var dayCount = data.hits[i];
            if (!adiData[dayCount.date]) {
                adiData[dayCount.date] = {};
            }

            if (versions.indexOf(dayCount.version) > -1) {
                adiData[dayCount.date][dayCount.version] = {
                    count: dayCount.adi_count,
                    build: dayCount.build_type,
                };
            }

            // Handle beta versions.
            for (var k = betaVersions.length - 1; k >= 0; k--) {
                if (dayCount.version.indexOf(betaVersions[k]) > -1) {
                    if (!adiData[dayCount.date][betaVersions[k]]) {
                        adiData[dayCount.date][betaVersions[k]] = {
                            count: 0,
                            build: dayCount.build_type,
                        };
                    }

                    adiData[dayCount.date][betaVersions[k]].count += dayCount.adi_count;
                }
            }
        }
        return adiData;
    }

    /**
     * Simply pass the data about build types.
     */
    function onBuildTypesData(data) {
        return data.hits;
    }

    /**
     * Show an error if any of the required services failed.
     */
    function onQueryError(jqXHR, textStatus, errorThrown) {
        $('.loading').remove();

        removeGraph();
        $('.message', container)
            .show()
            .empty()
            .append('There was an error processing the request: Status: ' + textStatus + ' Error: ' + errorThrown);
    }

    /**
     * Show an error if an argument fails to validate.
     */
    function onArgumentError(arg, message) {
        $('.loading').remove();

        removeGraph();
        $('.message', container)
            .show()
            .empty()
            .append('Error validating argument "' + arg + '": ' + message);
    }

    function showShardsErrors(errors) {
        $('.message', container)
            .show()
            .append(
                $('<p><b>Warning:</b> Our database is experiencing troubles, the data you see might be wrong. The team has been notified of the issue. </p>')
            );

        errors.forEach(function (error) {
            if (error.type === 'shards') {
                addShardWarning(error);
            }
        });
    }

    /**
     * Show a warning when a shard is failing in the database.
     */
    function addShardWarning(error) {
        var week = error.index.slice(-2);
        var year = error.index.slice(-6, error.index.length - 2);
        var firstDay = getDateOfISOWeek(year, week);
        var percent = error.shards_count * 100 / esShardsPerIndex;

        $('.message', container)
            .append(
                $('<p>The data for the week of ' + firstDay.toDateString() + ' is ~' + percent + '% lower than expected.</p>')
            );
    }

    /**
     * Called every time a service has stored some data. When all expected
     * data is received, proceed with mixing that data and showing the graph.
     */
    function onDataComplete(builds, adi, superSearch) {
        if (adi === null) {
            // This product likely has no ADI.
            $('#homepage-graph .title h2').text('Crashes per Day');
        }
        else {
            for (var i = 0, ln = superSearch.length; i < ln; i++) {
                var versionData = superSearch[i];
                var version = versions[i];
                var invalidData = [];

                for (var j = 0, lm = versionData.length; j < lm; j++) {
                    var day = dateIsoFormat(versionData[j].date);
                    if (!adi[day] || !adi[day][version]) {
                        versionData[j].count = null;
                        invalidData.push(j);
                    }
                    else {
                        var adis = adi[day][version];
                        var throttle = builds[adis.build];
                        versionData[j].count = 100.0 * versionData[j].count / adis.count / throttle;
                    }
                }

                if (invalidData.length === versionData.length) {
                    // All of the data for that version is invalid, let's just
                    // remove it to avoid errors with the graph library.
                    superSearch[i] = [];
                }
            }
        }

        drawGraph(superSearch);
    }

    /**
     * Show a graph of crash count per day and per version, divided by ADI
     * count and by throttle.
     */
    function drawGraph(data) {
        $('.loading').remove();

        MG.data_graphic({
            data: data,
            full_width: true,
            target: '#homepage-graph-graph',
            x_accessor: 'date',
            y_accessor: 'count',
            axes_not_compact: true,
            utc_time: true,
            interpolate: 'basic',
            area: false,
            legend: versions,
            legend_target: '#homepage-graph-legend',
            show_secondary_x_label: false,
        });
    }

    function removeGraph() {
        $('#homepage-graph-graph').empty();
        $('#homepage-graph-legend').empty();
    }

    /**
     * Load the data needed to build the graph from the public API.
     */
    function loadData() {
        socorro.ui.setLoader('#homepage-graph');

        // Validate duration is not bigger than 4 weeks.
        if (duration > 28) {
            return onArgumentError('days', 'duration cannot be bigger than 28 days');
        }

        // Hide any previous error.
        $('.message', container).hide();

        // Load data from the server. Graph building will be triggered when
        // receiving the data.
        $.when(
            queryBuildTypes().promise(),
            queryADI().promise(),
            querySuperSearch().promise()
        )
        .done(onDataComplete);
    }

    updateDates();
    loadData();

    // Apply the same colors as for the graph's legend to the version headers.
    $('#release_channels h4').each(function (index) {
        $(this).css('color', COLORS[index]);
    });
});
