# -*- coding: utf-8 -*-
from django import forms
from django.core.validators import FileExtensionValidator
from .validators import csv_content_validator

class UploadFileForm(forms.Form):
    institution_list = [
        ("BXSA", 'Bordeaux Sciences Agro'),
        ("INP", 'INP Bordeaux'),
        ("IEP", 'Sciences Po Bordeaux'),
        ("UBM", 'Université Bordeaux Montaigne'),
        ("UB", 'Université de Bordeaux'),
    ]
    institution = forms.ChoiceField(choices=institution_list, required=True, label='Choix de l''institution') 
    base_list = [   ('TEST', 'Lancer le traitement en base de test'),
                    ('PROD', 'Lancer le traitement en base de production')]
    base = forms.ChoiceField(choices=base_list, required=True, label='Sur quelle base lancer l''analyse') 
    file = forms.FileField(label='Télécharger le fichier de à traiter', validators=[csv_content_validator])