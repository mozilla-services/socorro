(function() {
    'use strict';
    /* https://github.com/ossreleasefeed/ujumbe */
    var ujumbe = {
        /**
         * Polyfils event.preventDefault in IE8
         * @param {object} event - The triggered event.
         */
        preventDefault: function(event) {
            if (!event.preventDefault) {
                Event.prototype.preventDefault = function() {
                    this.returnValue = false;
                };
            }
            event.preventDefault();
        },
        /**
         * Handles the close click event for ujumbe notifications.
         * @param {string} domParentNode - Valid CSS selector or Element node for parent container.
         * @param {object} event - The triggered event.
         */
        handleClickEvent: function(domParentNode, event) {
            // event.srcElement for IE8 support
            var eventTarget = event.target || event.srcElement;
            var eventTargetParentClassNames = eventTarget.offsetParent.getAttribute('class');

            // Only respond to the event if it originated from an ujumbe notification.
            if (eventTargetParentClassNames.indexOf('ujumbe') > -1) {
                ujumbe.preventDefault(event);
                ujumbe.removeUserMsg(domParentNode);
            }
        },
        /**
         * Returns the close button and attached the required event handler to the parent container.
         * @param {string} domParentNode - Valid CSS selector or Element node for parent container.
         * @returns closeButton - The close button as a HTMLButtonElement [http://mdn.io/HTMLButtonElement]
         */
        getCloseButton: function(domParentNode) {
            var closeButton = document.createElement('button');
            var closeText = document.createTextNode('x');

            closeButton.appendChild(closeText);
            closeButton.setAttribute('class', 'close');
            closeButton.setAttribute('title', 'Close Notification');

            if (!Element.prototype.addEventListener) {
                // IE8 and below
                domParentNode.attachEvent('onclick', function(event) {
                    ujumbe.handleClickEvent(domParentNode, event);
                });
            } else {
                domParentNode.addEventListener('click', function(event) {
                    ujumbe.handleClickEvent(domParentNode, event);
                });
            }

            return closeButton;
        },
        /**
         * Fades the notification message in declining steps of 20% from 100% to 0%.
         * @param {object} domParentNode - The parent of the notification element to fade.
         */
        fadeNotification: function(domParentNode) {
            var notification = domParentNode.querySelector('.ujumbe-notification');
            // get the opacity from the element but, limit it to one decimal point.
            var opacity = getComputedStyle(notification).opacity.substr(0, 3);

            if (opacity > 0) {
                notification.style.opacity = opacity - 0.2;

                setTimeout(function() {
                    ujumbe.fadeNotification(domParentNode);
                }, 60);
            } else {
                ujumbe.removeUserMsg(domParentNode);
            }
        },
        /**
         * Removes a previously set ujumbe notification.
         * @param {string} domParentNode - Valid CSS selector or Element node for parent container.
         */
        removeUserMsg: function(domParentNode) {

            if (typeof domParentNode === 'string') {
                domParentNode = document.querySelector(domParentNode);
            }

            var ujumbeNotification = domParentNode.querySelector('.ujumbe-notification');
            if (ujumbeNotification) {
                domParentNode.removeChild(ujumbeNotification);
            }
        },
        /**
         * Shows a user notification message attached to the specified parent element.
         * @param {string} parentSelector - Valid CSS selector for parent container.
         * @param {object} options - Specified options for the notification.
         */
        showUserMsg: function(parentSelector, options) {

            this.removeUserMsg(parentSelector);

            var domParentNode = document.querySelector(parentSelector);
            var insertPos = options.position || 'afterbegin';
            var message = options.message;

            if (!message) {
                var messageContainer = document.querySelector('#ujumbe');

                if (messageContainer.dataset) {
                    message = messageContainer.dataset[options.status];
                } else {
                    // If this is IE < 11, we need to get the data attributes explicitly as it does not
                    // support the dataset property.
                    message = messageContainer.getAttribute('data-' + options.status);
                }
            }

            var notification = document.createElement('div');
            var notificationMessage = document.createTextNode(message);
            notification.setAttribute('class', 'ujumbe-notification ' + options.status);
            notification.appendChild(notificationMessage);

            if (options.type === 'closeable') {
                notification.appendChild(ujumbe.getCloseButton(domParentNode));
            }

            if (options.type === 'autofade') {
                var autoFadeWaitTime = options.autoFadeWaitTime || 3000;

                setTimeout(function() {
                    if(typeof getComputedStyle !== 'undefined') {
                        ujumbe.fadeNotification(domParentNode);
                    } else {
                        // This is IE8 and below, just remove the notification.
                        ujumbe.removeUserMsg(domParentNode);
                    }
                }, autoFadeWaitTime);
            }

            domParentNode.insertAdjacentHTML(insertPos, notification.outerHTML);
        }
    };

    // expose ujumbe to the global object.
    window.ujumbe = ujumbe;

})();
