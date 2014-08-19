/*global: ALL_PERMISSIONS */

$(function () {
    'use strict';

    var formElt = $('#supersearch-field');

    $('input[name=name]', formElt).select2({
        'tags': [],
        'maximumSelectionSize': 1,
        'width': 'element'
    });

    $('input[name=namespace]', formElt).select2({
        'tags': [
            'processed_crash',
            'raw_crash'
        ],
        'maximumSelectionSize': 1,
        'width': 'element'
    });

    $('input[name=in_database_name]', formElt).select2({
        'tags': [],
        'maximumSelectionSize': 1,
        'width': 'element'
    });

    var queryTypeElt = $('select[name=query_type]', formElt);
    queryTypeElt.select2({
        'width': 'element'
    });
    if (queryTypeElt.data('selected')) {
        queryTypeElt.select2('val', queryTypeElt.data('selected'));
    }

    var dataValidationTypeElt = $('select[name=data_validation_type]', formElt);
    dataValidationTypeElt.select2({
        'width': 'element'
    });
    if (dataValidationTypeElt.data('selected')) {
        dataValidationTypeElt.select2('val', dataValidationTypeElt.data('selected'));
    }

    $('input[name=permissions_needed]', formElt).select2({
        'tags': ALL_PERMISSIONS,
        'width': 'element'
    });

    $('input[name=form_field_choices]', formElt).select2({
        'tags': [],
        'width': 'element'
    });

});
