(function( window, undefined ) {
    "use strict";
    var socorro = {
        date: {
            ONE_DAY: 1000 * 60 * 60 * 24,
            now: function() {
                return new Date();
            },
            //this will be more generic, for now, it expects a date string of the format mm/dd/yyyy
            // it converts this into the formate new Date expects, and returns a unformatted JavaScript 
            // date object
            convertToDateObj: function(dateString) {
                var dateStringSplit = dateString.split("/");
                return new Date(dateStringSplit[2], dateStringSplit[1] - 1, dateStringSplit[0]);
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
    
                var returnDate, day, month, year;
                
                if(format === "US_NUMERICAL") {
                    day = this.addLeadingZero(date.getDate());
                    //months are zero based so we need to add one
                    month = this.addLeadingZero(date.getMonth() + 1);
                    year = date.getFullYear();
                
                    returnDate = day + "/" + month + "/" + year;
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