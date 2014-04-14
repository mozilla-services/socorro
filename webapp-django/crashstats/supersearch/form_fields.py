from django import forms


OPERATORS = (
    '__true__', '__null__', '$', '~', '^', '=', '<=', '>=', '<', '>',
    '!__true__', '!__null__', '!$', '!~', '!^', '!=', '!'
)


def split_on_operator(value):
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
            self.operator, value = split_on_operator(value)

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


class MultipleValueField(forms.MultipleChoiceField):
    """This is the same as a MultipleChoiceField except choices don't matter
    as no validation will be done. The advantage is that it will take a list
    as input, and output a list as well, allowing several values to be passed.

    In the end, it's like a CharField that can take a list of values. It is
    used as the default field for supersearch.
    """

    def validate(self, value):
        pass


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


class StringField(MultipleValueField):
    """A CharField with a different name, to be considered as a string
    by the dynamic_form.js library. This basically enables string operators
    on that field ("contains", "starts with"... ).
    """
    pass


class BooleanField(forms.CharField):
    def to_python(self, value):
        """Return None if the value is None. Return 'true' if the value is one
        of the accepted values. Return 'false' otherwise.

        Return boolean values as a string so the middleware doesn't exclude
        the field if the value is False.
        """
        if value is None:
            return None
        if str(value).lower() in ('__true__', 'true', 't', '1', 'y', 'yes'):
            return 'true'
        return 'false'
