from django import forms
from .models import PickupLocation

class AddRdvForm(forms.Form):
    id_lecteur = forms.CharField(label='Identifiant du lecteur', max_length=100)
    library = forms.ModelChoiceField(label='Bibliothèque',queryset=PickupLocation.objects.all(), required=True)
    is_peb = forms.BooleanField(label='Demande de PEB ?',required=False)
        # date_rdv = forms.DateTimeField(label='Date', required=True)
