SignatureReport.Panel = function (panelName, onDelete) {

    // For accessing this from inside functions.
    var that = this;

    // Make the HTML elements.
    this.$panelElement = $('<div>', {'class': 'panel tab-inner-panel'});
    var $headerElement = $('<div>', {'class': 'title'});
    var $headingElement = $('<h2>', {
        'text': SignatureReport.capitalizeHeading(panelName)
    });
    var $deleteButton = $('<div>', {
        'class': 'options delete',
        'text': 'X'
    });
    var $bodyElement = $('<div>', {'class': 'body'});
    this.$contentElement = $('<div>', {'class': 'content'});

    // Bind the delete function to the delet button.
    $deleteButton.on('click', function (e) {
        e.preventDefault();
        that.$panelElement.remove();
        // Check that onDelete is not undefined
        if (onDelete) {
            onDelete();
        }
    });

    // Append everything.
    SignatureReport.addLoaderToElement(this.$contentElement);
    this.$panelElement.append(
        $headerElement.append(
            $headingElement,
            $deleteButton
        ),
        $bodyElement.append(
            this.$contentElement
        )
    );

};
