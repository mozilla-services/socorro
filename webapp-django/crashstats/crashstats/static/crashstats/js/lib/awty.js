/*
awty.js
version: 1.0
author: Schalk Neethling
license: MIT [github.com/ossreleasefeed/arewethereyet/blob/master/LICENSE]
URL: github.com/ossreleasefeed/arewethereyet
*/
(function() {

    var awty = {
        progress: null,
        selector: 'body',
        position: 'afterbegin',
        bgcolor: '#000',
        /**
         * Sets user preferences for progress meter.
         * @param {object} options - The custom options.
         */
        setOptions: function(options) {

            if (options.selector) {
                this.selector = options.selector;
            }

            if (options.position) {
                this.position = options.position;
            }

            if (options.bgcolor) {
                this.progress.style.backgroundColor = options.bgcolor;
            }
        },
        /**
         * Increases the progress meter to the specified percentageComplete.
         * @param {int} percentageComplete - An percentageComplete between 0 - 100
         */
        update: function(percentageComplete) {

            // When the meter has reached 100%, it's height property is
            // set to 0, if this then is the case, just clear out the
            // height property so it is applied from the stylesheet.
            var progressHeight = this.progress.style.height.substr(0, 1);
            if(progressHeight === '0') {
                this.progress.style.height = '';
            }

            if (percentageComplete < 100) {
                this.progress.style.width = percentageComplete + '%';
            } else {
                this.progress.style.width = percentageComplete + '%';
                window.setTimeout(function() {
                    awty.progress.style.width = 0;
                    awty.progress.style.height = 0;
                }, 1000);
            }
        },
        /**
         * Add a progress meter to the page. Inserts the meter based on the
         * specified parent or, defaults to the body.
         * @param {object} options - The options for the progress meter.
         */
        add: function(options) {

            // Only create a new element if progress does not already exist.
            if (!this.progress) {
                this.progress = document.createElement('div');
                this.progress.setAttribute('class', 'awty-progress');

                if (options) {
                    this.setOptions(options);
                }
            }

            var domParentNode = document.querySelector(this.selector);
            domParentNode.appendChild(this.progress);
        }
    };

    window.awty = awty;

})();
