/*global socorro:false, json_path:false, init_ver:false, init_prod:false */
$(function() {
    "use strict";
    var fromDate, toDate,
    graph, graphData, base_url,
    selectedVersion, selectedProduct,
    previousPoint = null,
    previousSeriesIndex = null,
    incorrectDateRange = "<p>The 'To' date should be greater than the 'From' date.</p>",
    noProductSelected = "<p>Please select a product below.</p>",
    dateFields = $("#nightly_crash_trends input[type='date']"),
    endDateWrapper = $("#end_date").parents(".field"),
    productsWrapper = $("#product").parents(".field"),
    dateSupported = function() {
        var inputElem = document.createElement("input");
        inputElem.setAttribute("type", "date");
        
        return inputElem.type !== "text" ? true : false;
    },
    showTooltip = function(x, y, contents) {
        $('<div id="graph-tooltip">' + contents + '</div>').css({
            top: y + 5,
            left: x + 5
        }).appendTo("body").fadeIn(200);
    },
    validateDateRange = function(fromDate, toDate) {
        return socorro.date.convertToDateObj(fromDate) < socorro.date.convertToDateObj(toDate);
    },
    showMsg = function(msg, type) {
        $(type).empty().append(msg).show();
    },
    resetForm = function() {
        $("p", endDateWrapper).remove();
        endDateWrapper.removeClass("error-field");

        $("p", productsWrapper).remove();
        productsWrapper.removeClass("error-field");
    },
    validateForm = function(start, end, product) {
        var formValid = true;

        //remove any previous validation messages
        resetForm();

        if(!validateDateRange(fromDate, toDate)) {
            endDateWrapper.addClass("error-field").append(incorrectDateRange);
            formValid = false;
        }

        if(product === "none") {
            productsWrapper.addClass("error-field").append(noProductSelected);
            formValid = false;
        }

        return formValid;
    },
    get_versions = function(initialize) {
        var versions = [],
        versionSelector = $("#version"),
        selectedProduct = $("#product").val(),
        optionElement = "",
        versionTxt = "",
        optionElements = [];

        // clear any info messages
        $(".info").hide();
        // empty versions selector before loading new versions
        versionSelector.empty();
        // remove error class from field
        $("p", productsWrapper).remove();
        productsWrapper.removeClass("error-field");

        //only make the ajax call if an actual product was selected.
        if(selectedProduct !== "none") {
            $.getJSON('/crash_trends/product_versions', { product: selectedProduct }, function(data) {
                if(data.length) {
                    versions = [];
        
                    $(data).each(function(i, version) {
                        optionElement = document.createElement('option');
                        optionElement.setAttribute("value", version);
                        //if this is our initial load, set the init version to selected
                        if(initialize && version === init_ver) {
                            optionElement.setAttribute("selected", "selected");
                        }
                        versionTxt = document.createTextNode(version);
                        optionElement.appendChild(versionTxt);
                        optionElements.push(optionElement);
                    });
                    
                    versionSelector.empty().append(optionElements);
                } else {
                    showMsg("No versions found for product", ".info");
                }
            }).error(function(jqXHR, textStatus, errorThrown) {
                showMsg(errorThrown, ".error");
            });
        }
    },
    setProductFilters = function() {
        $("#product option[value='" + init_prod +"']").attr("selected", "selected");
        // load the versions for the current product and set
        // the init version as selected
        get_versions(true);
    };

    var drawCrashTrends = function(url, init_ver) {
        var dates = socorro.date.getAllDatesInRange(fromDate, toDate, "US_NUMERICAL"),
        selectedVersion = init_ver === undefined ? $("#version option:selected").val() : init_ver,
        numberOfDates = dates.length,
        ajax_path = url === undefined ? json_path : url,
        i = 0,
        options = {
            colors: ["#058DC7", "#ED561B", "#50B432", "#990099"],
            grid: {
                hoverable: true
            },
            legend: {
                noColumns: 9,
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

            if(data.nightlyCrashes) {
                graph = $.plot("#nightly_crash_trends_graph", data.nightlyCrashes, options);
                //emty the ul before appending the new dates
                $("#dates").empty();
                for(i = numberOfDates - 1; i >= 0; i--) {
                    $("#dates").append("<li>" + dates[i] + " " + selectedVersion + "</li>");
                }
            } else {
                $("#nightly_crash_trends_graph").empty().append("No data found for selected criteria");
            }
        }).error(function(jqXHR, textStatus, errorThrown) {
            // remove the loading animation
            $("#loading").remove();
            $("#nightly_crash_trends_graph").empty().append(errorThrown);
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

        //set the product filters to the intial product and version
        setProductFilters();

        socorro.ui.setLoader(".report_graph");
        drawCrashTrends(undefined, init_ver);
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

        selectedProduct = $("#product").val();
        selectedVersion = $("#version").val();

        base_url = "/crash_trends/json_data?";
        fromDate = $("#start_date").val();
        toDate = $("#end_date").val();
        var params = {
            "product" : selectedProduct,
            "version" : selectedVersion,
            "start_date" : socorro.date.formatDate(socorro.date.convertToDateObj(fromDate), "ISO"),
            "end_date" : socorro.date.formatDate(socorro.date.convertToDateObj(toDate), "ISO")
        };

        //validate that toDate is after fromDate and a product is selected
        if(validateForm(fromDate, toDate, selectedProduct)) {
            //set the dates on the figcaption
            $("#fromdate").empty().append(fromDate);
            $("#todate").empty().append(toDate);
            
            $("title").empty().append("Crash Trends Report For " + selectedProduct + " " + selectedVersion);
            
            // add the loading animation
            socorro.ui.setLoader(".report_graph");
            drawCrashTrends(base_url + $.param(params));
        }
    });

    /*
     * when a selection is made from the product drop-down we need to call
     * the product_versions service to get the appropriate versions for the
     * selected product.
     */
    $("#product").change(function() {
        get_versions();
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
