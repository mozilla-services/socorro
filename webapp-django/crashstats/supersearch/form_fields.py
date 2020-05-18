# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import operator

import isodate

from django import forms
from django.utils.timezone import utc
from django.utils.encoding import smart_str

from crashstats.crashstats.utils import parse_isodate


OPERATORS = (
    "__true__",
    "__null__",
    "$",
    "~",
    "^",
    "@",
    "=",
    "<=",
    ">=",
    "<",
    ">",
    "!__true__",
    "!__null__",
    "!$",
    "!~",
    "!^",
    "!@",
    "!=",
    "!",
)


def split_on_operator(value):
    for op in sorted(OPERATORS, key=len, reverse=True):
        if value.startswith(op):
            value = value[len(op) :]
            return (op, value)

    return (None, value)


class PrefixedField:
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
        if isinstance(value, str):
            self.operator, value = split_on_operator(value)

        return super().to_python(value)

    def clean(self, *args, **kwargs):
        cleaned_value = super().clean(*args, **kwargs)

        self.prefixed_value = self.value_to_string(cleaned_value)
        if self.operator is not None and self.prefixed_value is not None:
            self.prefixed_value = self.operator + self.prefixed_value

        return cleaned_value

    def value_to_string(self, value):
        """Return the value as a string. """
        if value is None:
            return None
        return str(value)


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
    """Special field that uses SelectMultiple widget to deal with multiple values

    """

    def __init__(self, *args, **kwargs):
        kwargs["widget"] = forms.SelectMultiple
        super().__init__(*args, **kwargs)

    def clean(self, values, *args, **kwargs):
        cleaned_values = []
        prefixed_values = []
        operators = []

        if values is None:
            # call the mother classe's clean to do other verifications
            return super().clean(values, *args, **kwargs)

        for value in values:
            cleaned_value = super().clean(value, *args, **kwargs)
            if cleaned_value is not None:
                cleaned_values.append(cleaned_value)
                prefixed_values.append(self.prefixed_value)
                operators.append(self.operator)
        if operators and cleaned_values:
            self.validate_ordered_values(cleaned_values, operators)
        self.prefixed_value = prefixed_values
        return cleaned_values

    def validate_ordered_values(self, values, operators):
        operator_functions = {
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
        }
        for i, value in enumerate(values):
            op = operators[i]
            if op not in operator_functions:
                # Can only check those operators listed
                continue
            op_function = operator_functions[op]
            for j, other_value in enumerate(values):
                if i == j:
                    continue
                if not op_function(other_value, value):
                    raise forms.ValidationError(
                        "Operator combination failed {} {} {}".format(
                            value, op, other_value
                        )
                    )


class IntegerField(MultiplePrefixedValueField, forms.IntegerField):
    pass


class IsoDateTimeField(forms.DateTimeField):
    def to_python(self, value):
        if value:
            try:
                return parse_isodate(value).replace(tzinfo=utc)
            except (ValueError, isodate.isoerror.ISO8601Error):
                # let the super method deal with that
                pass

        return super().to_python(value)


class DateTimeField(MultiplePrefixedValueField, IsoDateTimeField):
    def value_to_string(self, value):
        if value:
            return value.isoformat()


class StringField(MultipleValueField):
    """A CharField with a different name, to be considered as a string
    by the dynamic_form.js library. This basically enables string operators
    on that field ("contains", "starts with"... ).

    """

    pass


class BooleanField(forms.CharField):
    truthy_strings = ("__true__", "true", "t", "1", "y", "yes")

    def to_python(self, value):
        """Return None if the value is None. Return 'true' if the value is one
        of the accepted values. Return 'false' otherwise.

        Return boolean values as a string so the middleware doesn't exclude
        the field if the value is False.
        """
        if value is None:
            return None

        if smart_str(value).lower() in self.truthy_strings:
            return "__true__"
        return "!__true__"
