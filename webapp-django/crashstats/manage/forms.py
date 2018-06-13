from django import forms

from crashstats.crashstats.forms import BaseForm


class GraphicsDeviceForm(BaseForm):

    vendor_hex = forms.CharField(max_length=100)
    adapter_hex = forms.CharField(max_length=100)
    vendor_name = forms.CharField(max_length=100, required=False)
    adapter_name = forms.CharField(max_length=100, required=False)


class GraphicsDeviceLookupForm(BaseForm):

    vendor_hex = forms.CharField(max_length=100)
    adapter_hex = forms.CharField(max_length=100)


class GraphicsDeviceUploadForm(BaseForm):

    file = forms.FileField()
    database = forms.ChoiceField(
        choices=(
            ('pcidatabase.com', 'PCIDatabase.com'),
            ('pci.ids', 'The PCI ID Repository (https://pci-ids.ucw.cz/)'),
        )
    )
