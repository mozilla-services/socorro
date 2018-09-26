from django import forms

from crashstats.crashstats.forms import BaseForm


class GraphicsDeviceUploadForm(BaseForm):

    file = forms.FileField()
    database = forms.ChoiceField(
        choices=(
            ('pcidatabase.com', 'PCIDatabase.com'),
            ('pci.ids', 'The PCI ID Repository (https://pci-ids.ucw.cz/)'),
        )
    )
