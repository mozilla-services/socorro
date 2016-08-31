/*global socorro:false, $:false */
(function( window, undefined ) {
    "use strict";
    var socorro = {
        ui: {
            /**
             * Loads an Ajax loader image and appends it to the specified container.
             *
             * @param {object} container           - The container to append the loader to (can also be
             *                                       a valid selector string).
             * @param {string} selector [optional] - A custom selector to use for the loader. This will be
             *                                       appended to the list of classes.
             * @param {boolean} inline [optional]  - Whether the loader should be set as an inlne or absolutely
             *                                       positioned element.
             */
            setLoader: function(container, selector, inline) {
                var classList = inline ? 'inline-loader' : 'loading';
                var isLoaderSet = false;

                if (typeof selector !== 'undefined') {
                    classList += ' ' + selector;
                    isLoaderSet = document.querySelector('.' + selector);
                }

                if(!isLoaderSet) {
                    var loader = new Image();
                    //set the class, alt and src attributes of the loading image
                    loader.setAttribute("class", classList);
                    loader.setAttribute("alt", "loading...");
                    loader.setAttribute("src", "/static/img/icons/ajax-loader.gif");

                    //append loader to it's container
                    $(container).append(loader);
                }
            },
            /**
             * Removes an Ajax loader image.
             * @param {string} selector [optional] - A custom selector to use when removing a specific loader.
             */
            removeLoader: function(selector) {
                var loaderClass = selector ? selector : 'loading';
                var loader = document.querySelector('.' + loaderClass);

                if (loader) {
                    loader.parentNode.removeChild(loader);
                }
            },
            removeUserMsg: function(selector) {
                var domParentNode = document.querySelector(selector);
                var errorMessage = domParentNode.querySelector('.error');
                var successMessage = domParentNode.querySelector('.success');

                if (errorMessage) {
                    domParentNode.removeChild(errorMessage);
                }

                if (successMessage) {
                    domParentNode.removeChild(successMessage);
                }
            },
            setUserMsg: function(selector, response, position) {

                // Remove any currently shown user messages in node.
                socorro.ui.removeUserMsg(selector);

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
                    return new Date(dateString);
                }
            },
            isFutureDate: function(date) {
                return this.convertToDateObj(date) > new Date();
            },
            /**
             * Returns whether the date range is valid based on the specified inequality.
             * ex. is adate < bdate will ensure the range is between an older and newer date
             * @param {string} adate - A date string of the format yyyy/mm/dd
             * @param {string} bdate - A date string of the format yyyy/mm/dd
             * @param {string} inequality - Valid values are less (<) or greater (>)
             */
            isValidDuration: function(adate, bdate, inequality) {
                adate = this.convertToDateObj(adate);
                bdate = this.convertToDateObj(bdate);

                return inequality === 'less' ? adate < bdate : adate > bdate;
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
             * ISO = "yyyy/mm/dd"
             * ISO_STANDARD = "yyyy-mm-dd"
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
                    returnDate = full_year + "/" + month + "/" + day;
                } else if(format === "ISO_STANDARD") {
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
        },
        search: {
            parseQueryString: function (queryString) {
                var params = {};
                var queries;
                var temp;
                var i;
                var len;

                // Split into key/value pairs
                queries = queryString.split("&");
                len = queries.length;

                if (len === 1 && queries[0] === '') {
                    return false;
                }

                // Convert the array of strings into an object
                for (i = 0; i < len; i++) {
                    temp = queries[i].split('=');
                    var key = temp[0];
                    var value = decodeURIComponent(temp[1]);

                    if (params[key] && Array.isArray(params[key])) {
                        params[key].push(value);
                    }
                    else if (params[key]) {
                        params[key] = [params[key], value];
                    }
                    else {
                        params[key] = value;
                    }
                }

                return params;
            },
            getFilteredParams: function (params) {
                if ('page' in params) {
                    delete params.page;
                }

                // Remove all private parameters (beginning with a _).
                for (var p in params) {
                    if (p.charAt(0) === '_') {
                        delete params[p];
                    }
                }

                return params;
            },
            sortResults: function (results, container, query) {
                if (query.term) {
                    return results.sort(function (a, b) {
                        if (a.text.length > b.text.length) {
                            return 1;
                        }
                        else if (a.text.length < b.text.length) {
                            return -1;
                        }
                        else {
                            return 0;
                        }
                    });
                }
                return results;
            },
        },
        dateSupported: function() {
            var inputElem = document.createElement("input");
            inputElem.setAttribute("type", "date");

            return inputElem.type !== "text" ? true : false;
        }
    };

    //expose socorro to the global object
    window.socorro = socorro;

})(window);
