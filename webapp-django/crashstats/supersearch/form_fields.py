from django import forms


OPERATORS = ('<=', '>=', '$', '<', '>', '~', '^')


def get_operator_from_string(value):
    for operator in sorted(OPERATORS, key=len, reverse=True):
        if value.startswith(operator):
            value = value[len(operator):]
            return (operator, value)
    return (None, value)


class PrefixedField(object):
    """Special field that accepts an operator as prefix in the value.

    Removes the prefix from the initial value before the validation process
    starts, and put it back in a different attribute once the validation
    process is finished. The cleaned value is the one without the prefix, thus
    allowing to use the real value and check its type.

    The validated, prefixed value is available in `prefixed_value` as a string,
    and the prefix is in `operator`.

    This is needed to allow fields like IntegerField to accept values
    containing an operator. For example, a value such as '>13' will raise
    a ValidationError in the basic django IntegerField. Using a PrefixedField
    based IntegerField, this value is perfectly valid.

    """

    operator = None
    prefixed_value = None

    def to_python(self, value):
        if isinstance(value, basestring):
            self.operator, value = get_operator_from_string(value)

        return super(PrefixedField, self).to_python(value)

    def clean(self, *args, **kwargs):
        cleaned_value = super(PrefixedField, self).clean(*args, **kwargs)

        self.prefixed_value = self.value_to_string(cleaned_value)
        if self.operator is not None:
            self.prefixed_value = self.operator + self.prefixed_value

        return cleaned_value

    def value_to_string(self, value):
        """Return the value as a string. """
        return unicode(value)


class MultiplePrefixedValueField(PrefixedField):
    """Special field that uses a SelectMultiple widget to deal with multiple
    values. """
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.SelectMultiple
        super(MultiplePrefixedValueField, self).__init__(*args, **kwargs)

    def clean(self, values, *args, **kwargs):
        cleaned_values = []
        prefixed_values = []

        if values is None:
            # call the mother classe's clean to do other verifications
            return super(MultiplePrefixedValueField, self).clean(
                values,
                *args,
                **kwargs
            )

        for value in values:
            cleaned_value = super(MultiplePrefixedValueField, self).clean(
                value,
                *args,
                **kwargs
            )
            cleaned_values.append(cleaned_value)
            prefixed_values.append(self.prefixed_value)

        self.prefixed_value = prefixed_values
        return cleaned_values


class IntegerField(MultiplePrefixedValueField, forms.IntegerField):
    pass


class DateTimeField(MultiplePrefixedValueField, forms.DateTimeField):
    def value_to_string(self, value):
        try:
            return value.isoformat()
        except AttributeError:  # when value is None
            return value
