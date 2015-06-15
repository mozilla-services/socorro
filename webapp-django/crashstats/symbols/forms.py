from django import forms
from crashstats.crashstats.forms import BaseForm


class UploadForm(BaseForm):
    file = forms.fields.FileField()

    valid_file_extensions = (
        '.zip',
        '.tgz',
        '.tar.gz',
        '.tar',
    )

    def clean_file(self):
        upload = self.cleaned_data['file']
        # check the file extension
        for extension in self.valid_file_extensions:
            if upload.name.lower().endswith(extension):
                # exit early
                return upload

        raise forms.ValidationError(
            "Unrecognized file (%r, %r)" % (
                upload.name,
                upload.content_type
            )
        )
