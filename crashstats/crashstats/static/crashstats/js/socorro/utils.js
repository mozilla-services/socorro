/*global socorro:false, $:false */
(function( window, undefined ) {
    "use strict";
    var socorro = {
        ui: {
            setLoader: function(container, selector) {
                var loaderClass = selector ? selector : "loading",
                loader = new Image(),
                isLoaderSet = document.querySelectorAll("." + loaderClass).length;

                if(!isLoaderSet) {
                    //set the class, alt and src attributes of the loading image
                    loader.setAttribute("class", loaderClass);
                    loader.setAttribute("alt", "graph loading...");
                    loader.setAttribute("src", "/static/img/icons/ajax-loader.gif");

                    //append loader to it's container
                    $(container).append(loader);
                }
            },
            setUserMsg: function(selector, response, position) {
                var domParentNode = document.querySelector(selector),
                insertPos = position ? position : "afterbegin";
                if(response.status === "success") {
                    domParentNode.insertAdjacentHTML(insertPos, "<div class='success'>" + response.message + "</div>");
                } else {
                    domParentNode.insertAdjacentHTML(insertPos, "<div class='error'>" + response.message + "</div>");
                }
            }
        },
        date: {
            ONE_DAY: 1000 * 60 * 60 * 24,
            now: function() {
                return new Date();
            },
            // This function takes a date string and converts it to an unformatted
            // JavaScript Date object. Currently one of two possible date string
            // formats are supported. If nothing is passed to the 'format' parameter
            // the default of dd/mm/yy will be assumed. The second supported format
            // is the ISO8601 standard which if of the format yyyymmdd
            // @param dateString The string to convert to a Date object
            // @param form The date format of the string
            convertToDateObj: function(dateString, format) {
                if(format === "ISO8601") {
                    var origin = dateString,
                        year = origin.substring(0, 4),
                        month = origin.substring(4, 6),
                        day = origin.substring(6, 8);
                    return new Date(year, month - 1, day);
                } else {
                    var dateStringSplit = dateString.split("/");
                    return new Date(dateStringSplit[2], dateStringSplit[1] - 1, dateStringSplit[0]);
                }
            },
            addLeadingZero: function(number) {
                    return number > 9 ? number : "0" + number;
            },
            // add one day to the passed date
            addDay: function(currentDate) {
                return new Date(currentDate.getTime() + this.ONE_DAY);
            },
            /*
             * Initial very limited date format support
             * US_NUMERICAL = "dd/mm/yyyy"
             */
            formatDate: function(date, format) {

                var returnDate, day, month, full_year;
                day = this.addLeadingZero(date.getDate());
                //months are zero based so we need to add one
                month = this.addLeadingZero(date.getMonth() + 1);
                full_year = date.getFullYear();

                if(format === "US_NUMERICAL") {
                    returnDate = day + "/" + month + "/" + full_year;
                } else if(format === "ISO") {
                    returnDate = full_year + "-" + month + "-" + day;
                }

               return returnDate;
            },
            getAllDatesInRange: function(from, to, returnFormat) {
                var fromDate = null,
                toDate = null,
                shouldFormat = returnFormat !== undefined,
                dates = [];

                // if we received dates in the format dd/mm/yyyy then we need
                // to massage the date a little in order for new Date to return
                // the correct date.
                if((typeof from !== "object") && from.indexOf("/") > -1) {
                    fromDate = this.convertToDateObj(from);
                    toDate = this.convertToDateObj(to);
                }

                fromDate = fromDate || new Date(from);
                toDate = toDate || new Date(to);

                while (fromDate < toDate) {
                    //because the formatDate function returns a string and not a
                    //Date object, we need to store the date object and send this to
                    //the addDay function.
                    var currentDate = fromDate;

                    //if a return format for the dates have been specified,
                    // format the date first before adding to the array.
                    if(shouldFormat) {
                        fromDate = this.formatDate(fromDate, returnFormat);
                    }
                    dates.push(fromDate);

                    // add one day to the fromDate until from and to match
                    fromDate = this.addDay(currentDate);
                }
                // as a last step at the toDate to the end of the dates array
                toDate = shouldFormat ? this.formatDate(toDate, returnFormat) : toDate;
                dates.push(toDate);

                return dates;
            }
        }
    };

    //expose socorro to the global object
    window.socorro = socorro;

})(window);
