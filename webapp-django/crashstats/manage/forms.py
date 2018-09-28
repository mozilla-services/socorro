from django import forms

from crashstats.crashstats.forms import BaseForm


class GraphicsDeviceUploadForm(BaseForm):
    file = forms.FileField()
