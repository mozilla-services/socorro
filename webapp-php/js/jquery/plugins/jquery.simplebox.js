/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

(function($) {

    var methods = {
        show: function(options) {
            var wrapper = document.createElement("div"),
            closeButton = document.createElement("a"),
            boxContent = this,
            windowWidth = window.innerWidth,
            windowHeight = window.innerHeight,
            boxContentWidth = boxContent.width(),
            boxContentHeight = boxContent.height(),
            scrollDistance = window.scrollY,
            leftOffset = (windowWidth / 2) - (boxContentWidth / 2),
            topOffset = (windowHeight / 3) + scrollDistance;

            /* 
             * Adding ie7 classes for CSS style fixes. Cannot be sure that the user is already
             * doing this so, this is simply to ensure compatibility.
             * 
             * Have to use browser version detection here as the fix is just for IE7 and below.
             * Cannot find a feature that will allow for detection of IE7 except $.support.boxModel
             * but, then the browser needs to be in QuirksMode.
             */
            if(jQuery.browser.version === "7.0") {
                $("html").addClass("ie7");
            }

            $(wrapper).attr({
                "id" : "simplebox_wrapper"
            });

            $(wrapper).css({
                "width" : $(document).width(),
                "height" : $(document).height()
            });

            boxContent.css({
                "position" : "absolute",
                "top" : topOffset,
                "left" : leftOffset,
                "border-bottom-right-radius" : "10px",
                "z-index" : "999999"
            });

            $(closeButton).attr({
                "id" : "close_simplebox",
                "title" : "Close dialog",
                "accesskey" : "c"
            });

            $(closeButton).css("margin-left", (boxContentWidth - 10) + "px");

            $(closeButton).append("close dialog");
            
            boxContent.append(closeButton);

            /*
             * Because of IE, we cannot simply wrap the form with the wrapper as setting the opcaity on
             * the wrapper will also effect the dialog so, these need to be independant.
             */
            $("body").append(wrapper);
            boxContent.show();

            /*
             * IE, below version 9, does not support RGBA nor HSLA so opacity needs to be done via JavaScript
             * using a IE specific filter.
             */
            if($.support.changeBubbles === false) {
                $("#simplebox_wrapper").css("background-color", "#333333").fadeTo('fast', 0.5);
            }

            $("body").keyup(function(event) {
                if(event.which === 27) {
                    boxContent.simplebox('close');
                }
            });

            $("#close_simplebox").click(function(event) {
                event.preventDefault();
                boxContent.simplebox('close');
            });
        },
        close: function() {
            $("#simplebox_wrapper, #close_simplebox").remove();
            this.hide();
        }
    };

    $.fn.simplebox = function(method) {

        if ( methods[method] ) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || ! method ) {
            return methods.show.apply( this, arguments );
        }
    };

}(jQuery));
