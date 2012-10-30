/*global $:true, socorro:true, crashReportsByBuildDateTmpl:true, crashReportsByVersionTmpl:true, Mustache:true */
$(function() {
    "use strict";
    var chartContainer = $("#adu-chart"),
        product = "",
        version = "",
        baseURL = "/home/frontpage_json?",
        ajaxURL = "",
        hashString = "",
        currentHref = "",
        dateRangeType = "",
        dateRangeVal = "",
        dateRangeTypeValPattern = /(?!=)[a-zA-Z]{1,6}(?=:|$)/i,
        durationPattern = /\d{1,2}(?=:|$)/,
        durationValPattern = /(?!=)\d{1,6}(?=:|$)/,
        colours = ['#058DC7', '#ED561B', '#50B432', '#990099'],
        chartOpts = {
            xaxis: {
              mode: 'time',
              timeformat: "%b %d",
              minTickSize: [1, "day"]
            },
            yaxis: {
              min: 0
            },
            series: {
                lines: { show: true },
                points: {
                    show: true,
                    radius: 1
                },
                shadowSize: 0
            },
            colors: colours,
            grid: {
                color: '#606060',
                backgroundColor: '#ffffff',
                borderColor: '#c0c0c0',
                borderWidth: 0
            },
            legend: {}
        };

    var setSelected = function(item, container) {
        $(container).find('a').removeClass("selected");
        item.addClass("selected");
    },
    setSelectedByHash = function() {
        hashString = $.trim(window.location.hash);
        if(hashString.length) {
            if(dateRangeTypeValPattern.exec(hashString) !== null) {
                $("#date-range-type a").each(function() {
                    if($(this).attr("href").indexOf(dateRangeTypeValPattern.exec(hashString)) > -1) {
                        setSelected($(this), "#date-range-type");
                    }
                });
            }

            if(durationValPattern.exec(hashString) !== null) {
                $("#duration a").each(function() {
                    if($(this).attr("href").indexOf(durationValPattern.exec(hashString)) > -1) {
                        setSelected($(this), "#duration");
                    }
                });
            }
        }
    },
    manageHistory = function(key, value) {
        var newHashString = key + "=" + value,
            currentKeyValue = "";

        hashString = $.trim(window.location.hash);

        if(hashString.indexOf(key) === -1) {
            window.location.hash += hashString.length ? ":" + newHashString : newHashString;
        } else {
            if(key === "date_range_type") {
                currentKeyValue = dateRangeTypeValPattern.exec(hashString);
                if(currentKeyValue !== value) {
                    newHashString = hashString.replace(currentKeyValue, value);
                }
            } else {
                currentKeyValue = durationValPattern.exec(hashString);
                if(currentKeyValue !== value) {
                    newHashString = hashString.replace(currentKeyValue, value);
                }
            }
            window.location.hash = newHashString;
        }
    },
    buildAjaxURL = function() {
        product = $("#products_select").val(),
        version = $("#product_version_select").val(),
        ajaxURL = baseURL,
        hashString = window.location.hash,
        dateRangeVal = dateRangeTypeValPattern.exec(hashString);

        var isDateRangeSet = hashString.indexOf("date_range_type"),
            isDurationSet = hashString.indexOf("duration");

        if(product.length) {
            ajaxURL += "product=" + product;
        }

        if(version.length && version !== "Current Versions") {
            ajaxURL += "&versions=" + version;
        }

        if(isDateRangeSet !== -1) {
            ajaxURL +=  "&date_range_type=" + dateRangeVal;
        }

        if(isDurationSet !== -1) {
            ajaxURL += "&duration=" + durationPattern.exec(hashString)[0];
        }

        return ajaxURL;
    },
    buildCrashReports = function(data) {
        var useTmpl = data.date_range_type === "build" ? crashReportsByBuildDateTmpl : crashReportsByVersionTmpl,
            crashReportsHTML = Mustache.to_html(useTmpl, data),
            releaseChannelsContainer = $("#release_channels");

        releaseChannelsContainer.empty().append(crashReportsHTML);
        releaseChannelsContainer.find('h4').each(function(index, item) {
            $(this).css('color', colours[index]);
        });
    },
    drawGraph = function(ajaxURL) {
        socorro.ui.setLoader("#homepage-graph");
        $.getJSON(ajaxURL, function(data) {

            $(".loading").remove();

            buildCrashReports(data);

            if(data.count > 0) {
                var chartData = [
                    { data: data["ratio" + 1] },
                    { data: data["ratio" + 2] },
                    { data: data["ratio" + 3] },
                    { data: data["ratio" + 4] }
                ];
                $.plot(chartContainer, chartData, chartOpts);
            } else {
                chartContainer.empty().append("No Active Daily User crash data is available for this report.");
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            $(".loading").remove();
            chartContainer.empty().append("There was an error processing the request: Status: " + textStatus + " Error: " + errorThrown);
        });
    },
    handleClickEvent = function(anchor, container, key) {
        currentHref = anchor.attr("href");

        //set the clicked item to selected
        setSelected(anchor, container);

        dateRangeType = currentHref.substring(currentHref.indexOf('=') + 1);
        manageHistory(key, dateRangeType);
        drawGraph(buildAjaxURL());
    },
    init = function() {
        setSelectedByHash();
        drawGraph(buildAjaxURL());
    };

    $("#date-range-type a").click(function(event) {
        event.preventDefault();
        handleClickEvent($(this), "#date-range-type", "date_range_type");
    });

    $("#duration a").click(function(event) {
        event.preventDefault();
        handleClickEvent($(this), "#duration", "duration");
    });

    // initialize and draw graph on DOM ready
    init();
});
