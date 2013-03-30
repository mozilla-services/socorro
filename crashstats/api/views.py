import datetime

from django import http
#from django.shortcuts import render, redirect
from crashstats.crashstats import models
from crashstats.crashstats import utils


from django import forms


class MultipleStringField(forms.TypedMultipleChoiceField):
    """Field that do not validate if the field values are in self.choices"""

    def to_python(self, value):
        """Override checking method"""
        return map(self.coerce, value)

    def validate(self, value):
        """Nothing to do here"""
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'])


TYPE_MAP = {
    basestring: forms.CharField,
    list: MultipleStringField,
    datetime.date: forms.DateField,
    datetime.datetime: forms.DateTimeField,
    int: forms.IntegerField,
}


def fancy_init(self, model, *args, **kwargs):
    self.model = model
    self.__old_init__(*args, **kwargs)
    for parameter in model.get_annotated_params():
        required = parameter['required']
        name = parameter['name']

        if parameter['type'] not in TYPE_MAP:
            raise NotImplementedError(parameter['type'])
        field_class = TYPE_MAP[parameter['type']]
        self.fields[name] = field_class(required=required)


class FormWrapperMeta(forms.Form.__metaclass__):
    def __new__(cls, name, bases, attrs):
        attrs['__old_init__'] = bases[0].__init__
        attrs['__init__'] = fancy_init
        return super(FormWrapperMeta, cls).__new__(cls, name, bases, attrs)


class FormWrapper(forms.Form):
    __metaclass__ = FormWrapperMeta


# Names of models we don't want to serve at all
BLACKLIST = (
    #'RawCrash',
)


@utils.json_view
def model_wrapper(request, model_name):
    if model_name in BLACKLIST:
        raise http.Http404("Don't know what you're talking about!")
    try:
        model = getattr(models, model_name)
    except AttributeError:
        raise http.Http404('no model called `%s`' % model_name)
    instance = model()
    if request.method == 'POST':
        function = instance.post
    else:
        function = instance.get

    form = FormWrapper(model, request.REQUEST)
    if form.is_valid():
        result = function(**form.cleaned_data)
        # XXX
        # We might want to scan for any key in there called "email"
        # and delete it.
        # Or, "user_comments", "urls", Any more??
        # /XXX
    else:
        result = {'errors': dict(form.errors)}

    return result
