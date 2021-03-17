from django import forms
from .models import Library 

class UploadFileForm(forms.Form):
    library = forms.ModelChoiceField(label='Bibliothèque',queryset=Library.objects.all(), required=True)
    file = forms.FileField(label='Télécharger votre fichier de PPN')
    job_types_list = [  ("ALMA_TO_SUDOC", "Comparer les localisations Alma avec les localisations SUDOC"),
                        ("SUDOC_TO_ALMA", "Comparer les localisations SUDOC avec les localisations ALMA")]
    job_type = forms.ChoiceField(choices=job_types_list, required=True, label='Type d''analyse de recouvrement') 