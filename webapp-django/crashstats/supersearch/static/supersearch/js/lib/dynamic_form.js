/*jshint jquery: true */
(function ($) {
    'use strict';

    // String used to separate values in select2 fields.
    var VALUES_SEPARATOR = '|||';

    // All available operators.
    var OPERATORS = {
        'has': 'has terms',
        '!': 'does not have terms',
        '=': 'is',
        '!=': 'is not',
        '~': 'contains',
        '!~': 'does not contain',
        '^': 'starts with',
        '!^': 'does not start with',
        '$': 'ends with',
        '!$': 'does not end with',
        '@': 'matches regex',
        '!@': 'does not match regex',
        '>': '>',
        '>=': '>=',
        '<': '<',
        '<=': '<=',
        '__null__': 'does not exist',
        '!__null__': 'exists',
        '__true__': 'is true',
        '!__true__': 'is false'
    };

    // Order matters here, the first operator will be used as the default
    // value when no operator is passed for a field.
    var OPERATORS_BASE = ['has', '!'];
    var OPERATORS_RANGE = ['>', '>=', '<', '<='];
    var OPERATORS_REGEX = ['~', '=', '$', '^', '@', '!=', '!~', '!$', '!^', '!@'];
    var OPERATORS_EXISTENCE = ['__null__', '!__null__'];
    var OPERATORS_BOOLEAN = ['__true__', '!__true__'];

    var OPERATORS_ENUM = OPERATORS_BASE;
    var OPERATORS_NUMBER = OPERATORS_BASE.concat(OPERATORS_RANGE);
    var OPERATORS_DATE = OPERATORS_RANGE;
    var OPERATORS_STRING = OPERATORS_BASE.concat(OPERATORS_REGEX).concat(OPERATORS_EXISTENCE);

    var OPERATORS_NO_VALUE = OPERATORS_EXISTENCE.concat(OPERATORS_BOOLEAN);

    /**
     * Create a new dynamic form or run an action on an existing form.
     *
     * Actions:
     *     newLine - Add a new line to this dynamic form
     *     getParams - Return an object with the content of this dynamic form
     *     setParams - Change the content of this dynamic form
     *
     * If `action` is none of those values, create a new dynamic form where
     * the first argument is the URL of the JSON file describing the fields
     * and the optional second argument is an object containing the initial
     * form values.
     */
    function dynamicForm(action, initialParams, containerId, onReadyCallback, sortFuntion) {
        var form = this;
        var dynamic = form.data('dynamic');
        var lines = [];
        var container = form;

        if (dynamic) {
            lines = dynamic.lines;
            container = dynamic.container;
        }

        initialParams = initialParams || null;
        containerId = containerId || null;

        if (action === 'getOperatorsList') {
            return Object.keys(OPERATORS);
        }

        if (action === 'newLine' || action === 'getParams' || action === 'setParams') {
            if (!dynamic) {
                throw new Error('Impossible to call ' + action + ' on an object that was not initialized first');
            }

            if (action === 'newLine') {
                if (initialParams) {
                    // there is some data, this should not be a blank line
                    return dynamic.createLine(
                        initialParams.field,
                        initialParams.operator,
                        initialParams.value
                    );
                }
                return dynamic.newLine();
            }
            else if (action === 'getParams') {
                return dynamic.getParams();
            }
            else if (action === 'setParams') {
                return dynamic.setParams(initialParams);
            }
        }

        var fieldsURL = action;
        var fields = {};
        var sortedFieldNames = [];
        var lastFieldLineId = 0;

        if (containerId) {
            container = $(containerId, form);
        }

        // first display a loader while the fields data is being downloaded
        container.append($('<div>', {'class': 'loader'}));

        $.getJSON(
            fieldsURL,
            function(data) {
                $('.loader', container).remove();
                fields = data;
                sortedFieldNames = Object.keys(fields).sort();
                if (initialParams) {
                    setParams(initialParams);
                }

                if (onReadyCallback) {
                    onReadyCallback();
                }
            }
        );

        /**
         * Get the list of operators for a field.
         * @param field Field object extracted from the fields list.
         * @return object A dictionary of options, key is the option name, value is
         *                the option value to use in the select box.
         */
        function getOperatorsForField(field) {
            var options = OPERATORS_BASE;

            if (field.valueType === 'number') {
                options = OPERATORS_NUMBER;
            }
            else if (field.valueType === 'date') {
                options = OPERATORS_DATE;
            }
            else if (field.valueType === 'bool') {
                options = OPERATORS_BOOLEAN;
            }
            else if (field.valueType === 'flag') {
                options = OPERATORS_EXISTENCE;
            }
            else if (field.valueType === 'string') {
                options = OPERATORS_STRING;
            }
            else {  // type 'enum' or unknown type
                options = OPERATORS_ENUM;
            }

            return options;
        }

        /**
         * Get the parameters object, built from the field's values.
         * @param filters List of objects containing field, operator and value.
         * @return object A dictionary of parameters.
         */
        function buildParametersObject(filters) {
            var params = {};
            for (var f in filters) {
                var filter = filters[f];
                var value = null;

                if (filter.operator === OPERATORS_BASE[0]) {
                    value = filter.value.split(VALUES_SEPARATOR);
                }
                else {
                    value = filter.value.split(VALUES_SEPARATOR);
                    for (var i = value.length - 1; i >= 0; i--) {
                        value[i] = filter.operator + value[i];
                    }
                }

                if (params[filter.field] !== undefined) {
                    if (!Array.isArray(params[filter.field])) {
                        params[filter.field] = [params[filter.field]];
                    }
                    params[filter.field].push(value);
                }
                else {
                    params[filter.field] = value;
                }
            }

            return params;
        }

        /**
         * Return the parameters object of this dynamic form.
         */
        function getParams() {
            var filters = [];

            for (var l in lines) {
                var line = lines[l];
                var filter = line.get();

                if (filter) {
                    filters.push(filter);
                }
            }

            return buildParametersObject(filters);
        }

        /**
         * Create a new line with specific values.
         */
        function setParamLine(field, value) {
            var operator = getOperatorFromValue(value);
            var allowed_operators = getOperatorsForField(fields[field]);
            value = value.slice(operator.length);

            if (operator === '') {
                // if the operator is missing, use the default one
                operator = allowed_operators[0];
            }

            createLine(field, operator, value);
        }

        /**
         * Set the values of this form. The `params` format is the same as
         * what `getParams` returns. Operators are guessed from the values.
         */
        function setParams(params) {
            reset();

            for (var p in params) {
                if (p.charAt(0) === '_') {
                    // If the first letter of the field name is an underscore,
                    // that parameter should be ignored.
                    continue;
                }

                var param = params[p];
                var allowed_operators = getOperatorsForField(fields[p]);

                if (Array.isArray(param)) {
                    var valuesWithoutOperator = [];
                    param.forEach(function (value) {
                        if (!value) {
                            return;
                        }

                        var operator = getOperatorFromValue(value);
                        value = value.slice(operator.length);
                        if (operator) {
                            createLine(p, operator, value);
                        }
                        else {
                            valuesWithoutOperator.push(value);
                        }
                    });
                    if (valuesWithoutOperator.length > 0) {
                        createLine(p, allowed_operators[0], valuesWithoutOperator);
                    }
                }
                else {
                    setParamLine(p, param);
                }
            }
        }

        /**
         * Return the operator contained at the beginning of a string, if any.
         */
        function getOperatorFromValue(value) {
            // These operators need to be sorted by decreasing size.
            var operators = ['__true__', '__null__', '<=', '>=', '~', '$', '^', '=', '@', '<', '>', '!'];
            var prefix = '!';

            for (var i = 0, l = operators.length; i < l; i++) {
                var operator = operators[i];
                if (value.slice(0, operator.length) === operator) {
                    return operator;
                }

                var prefixed = prefix + operator;
                if (value.slice(0, prefixed.length) === prefixed) {
                    return prefixed;
                }
            }

            return '';
        }

        /**
         * Create a new, empty line in this form.
         */
        function newLine() {
            var line = new FormLine(container);
            line.createLine();
            lines.push(line);
        }

        /**
         * Create a new line in this form, and set its inputs' values.
         */
        function createLine(field, operator, value) {
            var line = new FormLine(container);
            line.createLine(true);
            line.createFieldInput(field);
            line.createOperatorInput(null, operator);

            // Only create the value line if the operator accepts values.
            if (OPERATORS_NO_VALUE.indexOf(operator) === -1) {
                line.createValueInput(null, value);
            }

            lines.push(line);
        }

        /**
         * Reset this form by removing all lines.
         */
        function reset() {
            var line = false;
            while (line = lines.pop()) {
                line.remove();
            }
        }

        /**
         * A line of the form. Handles DOM creation, events, and data.
         */
        var FormLine = function (container) {
            this.id = lastFieldLineId++;
            this.container = container;
        };

        /**
         * Create the new line.
         */
        FormLine.prototype.createLine = function (noField) {
            this.line = $('<fieldset>', { 'id': this.id });
            this.container.append(this.line);

            // Create an option to remove the line
            var deleteOption = $('<a>', {
                'class': 'dynamic-line-delete',
                'href': '#',
                'text': 'x'
            }).click(function (e) {
                e.preventDefault();
                this.remove();
            }.bind(this));
            this.line.append(deleteOption);

            if (!noField) {
                this.createFieldInput();
            }
        };

        /**
         * Create the field input.
         */
        FormLine.prototype.createFieldInput = function (field) {
            this.fieldInput = $('<select>', {
                'class': 'field',
                'data-placeholder': 'Choose a field'
            });
            this.fieldInput.append($('<option>'));

            sortedFieldNames.forEach(function(f) {
                this.fieldInput.append($('<option>', {
                    'value': f,
                    'text': fields[f].name
                }));
            }, this);
            this.line.append(this.fieldInput);

            this.fieldInput.select2({
                placeholder: 'Choose a field',
                width: 'element',
                sortResults: sortFuntion
            });
            this.fieldInput.on('change', this.createOperatorInput.bind(this));

            if (field) {
                this.fieldInput.select2('val', field);
            }
            else {
                this.fieldInput.select2('open');
            }
        };

        /**
         * Create the operator input.
         */
        FormLine.prototype.createOperatorInput = function (event, operator) {
            this.remove(['operatorInput', 'valueInput']);

            this.operatorInput = $('<select>', {
                'class': 'operator',
                'placeholder': 'Choose an operator'
            });
            this.operatorInput.append($('<option>'));

            var options = getOperatorsForField(fields[this.fieldInput.val()]);
            for (var i = 0, l = options.length; i < l; i++) {
                this.operatorInput.append($('<option>', {
                    'value': options[i],
                    'text': OPERATORS[options[i]]
                }));
            }

            this.line.append(this.operatorInput);

            this.operatorInput.select2({
                width: 'element'
            });
            this.operatorInput.on('change', function (e) {
                // We should create the value input only if there was no value
                // yet or the previous operator was a "no-value" one, and
                // the new operator accepts values.
                if (
                    OPERATORS_NO_VALUE.indexOf(e.added.id) === -1 && (
                        !e.removed ||
                        OPERATORS_NO_VALUE.indexOf(e.removed.id) > -1
                    )
                ) {
                    this.createValueInput();
                }
                else if (OPERATORS_NO_VALUE.indexOf(e.added.id) > -1) {
                    this.remove(['valueInput']);
                    newLine();
                }
            }.bind(this));

            if (operator) {
                if ($.inArray(operator, options) == -1) {
                    operator = options[0];
                }
                this.operatorInput.select2('val', operator);
            }
            else {
                this.operatorInput.select2('open');
            }
        };

        /**
         * Create the value input.
         */
        FormLine.prototype.createValueInput = function (event, value) {
            var field = fields[this.fieldInput.val()];
            var operator = this.operatorInput.val();
            var values = field.values || [];

            this.remove(['valueInput']);

            if (field.valueType === 'enum' && field.extendable === false) {
                this.valueInput = $('<select>', {
                    'class': 'value'
                });
                if (operator === 'in') {
                    this.valueInput.attr('multiple', 'multiple');
                }
                for (var i in values) {
                    this.valueInput.append($('<option>', {
                        'value': values[i],
                        'text': values[i]
                    }));
                }
            }
            else {
                this.valueInput = $('<input>', {
                    'type': 'text',
                    'class': 'value'
                });
            }
            this.line.append(this.valueInput);

            var selectParams = {
                'separator': VALUES_SEPARATOR,
                'width': 'element'
            };
            if (field.extendable !== false) {
                selectParams.tags = values;
            }
            if (field.multiple !== true) {
                selectParams.multiple = false;
            }

            this.valueInput.select2(selectParams);

            if (value || (Array.isArray(value) && value[0])) {
                var data = null;
                if (Array.isArray(value)) {
                    data = [];
                    for (var j = 0, l = value.length; j < l; j++) {
                        data.push({'id': value[j], 'text': value[j]});
                    }
                }
                else {
                    data = {'id': value, 'text': value};
                }
                this.valueInput.select2('data', data);
            }
            else if (typeof value === 'undefined') {
                // open only if value was not passed, which means only when
                // this field is created after a user selected an operator
                this.valueInput.select2('open');
            }

            // bind TAB key to create new line
            $('.select2-search-field input').on('keypress', function (e) {
                var TAB_KEY = 9;
                if (e.keyCode === TAB_KEY && !e.shiftKey && !e.ctrlKey && !e.altKey) {
                    newLine();
                }
            });
        };

        /**
         * Remove this line from the DOM, and delete its values.
         */
        FormLine.prototype.remove = function (inputs) {
            // If no parameter is passed, default to the list of all inputs
            if (!inputs) {
                inputs = ['fieldInput', 'operatorInput', 'valueInput'];

                // If we remove all fields, remove the entire line
                this.line.remove();
            }

            for (var i in inputs) {
                var input = inputs[i];

                if (this[input]) {
                    this[input].select2('destroy');
                    this[input].remove();
                    this[input] = null;
                }
            }
        };

        /**
         * Return the values of this line, if the line is complete.
         */
        FormLine.prototype.get = function () {
            if (this.fieldInput && this.operatorInput) {
                var field = this.fieldInput.val();
                var operator = this.operatorInput.val();
                var value = '';

                var isValueNeeded = OPERATORS_NO_VALUE.indexOf(operator) === -1;

                if (isValueNeeded && !this.valueInput) {
                    return null;
                }
                else if (isValueNeeded && this.valueInput) {
                    value = this.valueInput.val();
                }

                if (field && operator && (value || !isValueNeeded)) {
                    return {
                        'field': field,
                        'operator': operator,
                        'value': value
                    };
                }
            }
            return null;
        };

        // Expose the public functions of this form so the context is kept.
        form.data('dynamic', {
            newLine: newLine,
            createLine: createLine,
            getParams: getParams,
            setParams: setParams,
            lines: lines,
            container: container
        });

        return form;
    }

    $.fn.dynamicForm = dynamicForm;
})(jQuery);
