(function(window, undefined) {

    'use strict';

    var accordion = {
        container: null,
        /**
         * Hides all content panes in current accordion container.
         * @params {array} contentPanes - The panes to hide.
         */
        hidePanes: function(contentPanes) {
            var panesLength = contentPanes.length;

            for (var i = 0; i < panesLength; i++) {
                var classArray = contentPanes[i].getAttribute('class').split(/\s/);
                var index = classArray.indexOf('show');

                if (index > -1) {
                    classArray.splice(index, 1);
                    // we are collapsing so, update aria-expanded
                    contentPanes[i].setAttribute('aria-hidden', 'true');
                    // @see https://developer.mozilla.org/en-US/docs/Web/API/NonDocumentTypeChildNode.previousElementSibling
                    contentPanes[i].previousElementSibling.setAttribute('aria-expanded', 'false');
                }
                contentPanes[i].setAttribute('class', classArray.join(' '));
            }
        },
         /**
         * Shows the triggered content pane.
         * @params {object} pane - The pane to show.
         */
        showPane: function(pane) {
            var classes = pane.getAttribute('class');
            pane.setAttribute('class', classes + ' show');
            // as this pane is now expanded, update aria-hidden.
            pane.setAttribute('aria-hidden', 'false');
            pane.focus();
        },
        /**
         * Handles all events triggered within the accordion container.
         * @params {object} event - The event that was fired.
         */
        handleEvent: function(event) {
            var anchor = event.target;
            var contentPanelId = anchor.getAttribute('href');

            var parent = event.target.parentNode;
            var parentRole = parent.getAttribute('role');
            var parentExpandedState = parent.getAttribute('aria-expanded');

            // only handle event if the parent has a role of tab.
            // if the tab is currently expanded, collapse it
            if (parentRole === 'tab' && parentExpandedState === 'true') {
                event.preventDefault();

                // set the clicked tab as collapsed and not selected.
                parent.setAttribute('aria-expanded', 'false');
                parent.setAttribute('aria-selected', 'false');

                // hide all the panes
                this.hidePanes(this.container.querySelectorAll('.content-pane'));
            } else if (parentRole === 'tab') {
                event.preventDefault();

                // set the newly selected tab as expanded and selected.
                parent.setAttribute('aria-expanded', 'true');
                parent.setAttribute('aria-selected', 'true');

                // hide all the panes
                this.hidePanes(this.container.querySelectorAll('.content-pane'));

                // show the selected pane
                this.showPane(document.querySelector(contentPanelId));
            }
        },
        /**
         * Handles events delegated to the accordion.
         * @param {object} event - The event to handle
         */
        handleKeyboardEvent: function(event) {
            // Chrome does not support event.key so, we fallback to keyCode
            var key = event.key ? event.key : event.keyCode;

            // handle enter and spacebar keys.
            if ((key === 13 || key === 32) ||
                (key === 'Enter' || key === 'Spacebar')) {
                this.handleEvent(event);
            }
        },
        /**
         * Delegates keyboard events either back to the browser or, stops propogation
         * and calls handleKeyboardEvent to handle the key event.
         * @params {object} event - The event to delegate
         */
        delegateKeyEvents: function(event) {
            var key = event.key ? event.key : event.keyCode;

            switch(key) {
                case 13:
                case 32:
                case 'Enter':
                case 'Spacebar':
                    event.stopPropagation();
                    this.handleKeyboardEvent(event);
                    return false;
            }
            return true;
        },
        init: function(accordionContainer) {

            this.container = accordionContainer;

            this.container.addEventListener('click', function(event) {
                // handle edge cases where the original event.targer is removed
                // riht after the event was trigered causing event.target.parentNode
                // in handleEvent to be null.
                if(event.target.parentNode) {
                    accordion.handleEvent(event);
                }
            }, false);

            this.container.addEventListener('keyup', function(event) {
                if(event.target.parentNode) {
                    accordion.delegateKeyEvents(event);
                }
            });

            this.container.addEventListener('keydown', function(event) {
                if(event.target.parentNode) {
                    accordion.delegateKeyEvents(event);
                }
            });
        }
    };

    // Expose accordion to the global object
    window.accordion = accordion;

})(window);
