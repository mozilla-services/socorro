from django import forms
from crashstats.crashstats.forms import BaseModelForm
from . import models


class UploadForm(BaseModelForm):

    valid_content_types = (
        'application/zip',
        'application/x-tar',
        'application/x-gzip',
    )

    class Meta:
        model = models.SymbolsUpload
        fields = ('file',)

    def clean_file(self):
        upload = self.cleaned_data['file']
        ct = upload.content_type
        if ct not in self.valid_content_types:
            raise forms.ValidationError(
                "Unrecognized file content type %r" % ct
            )
        return upload
