/*global socorro:false */
$(function() {
    "use strict";
    var fromDate, toDate,
    graph, graphData, base_url,
    selectedVersion, selectedProduct,
    previousPoint = null,
    previousSeriesIndex = null,
    errorMsg = "The 'To' date should be greater than the 'From' date.",
    dateFields = $("#nightly_crash_trends input[type='date']"),
    dateSupported = function() {
        var inputElem = document.createElement("input");
        inputElem.setAttribute("type", "date");
        
        return inputElem.type !== "text" ? true : false;
    },
    setLoader = function() {
        var loader = new Image();
        //set the id, alt and src attributes of the loading image
        loader.setAttribute("id", "loading");
        loader.setAttribute("alt", "graph loading...");
        loader.setAttribute("src", "/img/icons/ajax-loader.gif");
        
        //append loader to report graph container
        $(".report_graph").append(loader);
    },
    showTooltip = function(x, y, contents) {
        $('<div id="graph-tooltip">' + contents + '</div>').css({
            top: y + 5,
            left: x + 5
        }).appendTo("body").fadeIn(200);
    },
    validateDateRange = function(fromDate, toDate) {
        return socorro.date.convertToDateObj(fromDate) < socorro.date.convertToDateObj(toDate);
    };
    
    var drawCrashTrends = function(url) {
        var dates = socorro.date.getAllDatesInRange(fromDate, toDate, "US_NUMERICAL"),
        selectedVersion = $("#version option:selected").val(),
        numberOfDates = dates.length,
        ajax_path = url === undefined ? json_path : url,
        i = 0,
        options = {
            colors: ["#058DC7", "#ED561B", "#50B432", "#990099"],
            grid: {
                hoverable: true
            },
            legend: {
                noColumns: 8,
                container: "#graph_legend"
            },
            series: {
                stack: true,
                bars: {
                    show: true,
                    horizontal: true
                },
                points: {
                    show: true
                }
            },
            yaxis: {
                ticks: 0
            }
        };
        
        graphData = $.getJSON(ajax_path, function(data) {
            // remove the loading animation
            $("#loading").remove();
            
            graph = $.plot("#nightly_crash_trends_graph", data.nightlyCrashes, options);
            //emty the ul before appending the new dates
            $("#dates").empty();
            for(i = numberOfDates - 1; i >= 0; i--) {
                $("#dates").append("<li>" + dates[i] + " " + selectedVersion + "</li>");
            }
        }).error(function() {
            // remove the loading animation
            $("#loading").remove();
            $("#nightly_crash_trends_graph").append(graphData.responseText);
        });
    };
    
    var init = function() {
        toDate = socorro.date.formatDate(socorro.date.now(), "US_NUMERICAL");
        fromDate = socorro.date.formatDate(new Date(socorro.date.now() - (socorro.date.ONE_DAY * 6)), "US_NUMERICAL");
        
        //set the value of the input fields
        $("#start_date").val(fromDate);
        $("#end_date").val(toDate);
        
        //set the dates on the figcaption
        $("#fromdate").empty().append(fromDate);
        $("#todate").empty().append(toDate);
        
        setLoader();
        drawCrashTrends();
    };
    
    $("#nightly_crash_trends_graph").bind("plothover", function (event, pos, item) {
        
        var message = "";
        
        if (item) {
            
            //tracking the dataIndex assists with vertical mouse movement across the bars
            //tracking seriesIndex assists with horizontal movemnt across a bar
            if ((previousPoint !== item.dataIndex) || (previousSeriesIndex !== item.seriesIndex)) {
                
                $("#graph-tooltip").remove();
            
                previousPoint = item.dataIndex;
                previousSeriesIndex = item.seriesIndex;
                
                message = item.series.data[previousPoint][0] + " total crashes for builds " + item.series.label + " old.";
                
                showTooltip(item.pageX, item.pageY, message);
            }
        } else {
            $("#graph-tooltip").remove();
            previousPoint = null;
        }
    });
    
    $("#nightly_crash_trends").submit(function(event) {
        event.preventDefault();

        base_url = "/crash_trends/json_data?";
        fromDate = $("#start_date").val();
        toDate = $("#end_date").val();
        var params = {
            "product" : $("#product option:selected").val(),
            "version" : $("#version option:selected").val(),
            "start_date" : socorro.date.formatDate(socorro.date.convertToDateObj(fromDate), "ISO"),
            "end_date" : socorro.date.formatDate(socorro.date.convertToDateObj(toDate), "ISO")
        };

        //validate that toDate is after fromDate
        if(validateDateRange(fromDate, toDate)) {
            //remove any previous validation messages
            dateFields.removeClass("error-field");
            $(".error").hide();
            
            //set the dates on the figcaption
            $("#fromdate").empty().append(fromDate);
            $("#todate").empty().append(toDate);
            
            // add the loading animation
            setLoader();
            drawCrashTrends(base_url + $.param(params));
        } else {
            //validation failed raise validation message and highlight fields
            dateFields.addClass("error-field");
            $(".error").empty().append(errorMsg).show();
        }
    });
    
    //check if the HTML5 date type is supported else, fallback to jQuery UI
    if(!dateSupported()) {
        dateFields.datepicker({
            dateFormat: "dd/mm/yy"
        });
    }
    
    /*
     * On DOM ready we do our first call to draw the graph. The date range for this 
     * is today minus six days. From here on out, the user can choose to adjust the 
     * dates as required.
     */
    init();
    
});
