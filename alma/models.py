# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.utils.html import format_html

# Create your models here.

class ProcessUpdateItem(models.Model):
    UB = 'UB'
    UBM = 'UBM'
    BXSA = 'BXSA'
    IEP = 'IEP'
    INP = 'INP'
    INSTITUTION_CHOICES = [
        (BXSA, 'Bordeaux Sciences Agro'),
        (INP, 'INP Bordeaux'),
        (IEP, 'Sciences Po Bordeaux'),
        (UBM, 'Université Bordeaux Montaigne'),
        (UB, 'Université de Bordeaux'),
    ]
    PROD = 'PROD'
    TEST = 'TEST'
    BASE_CHOICES = [    (PROD, 'Lancer le traitement en base de production'),
                        (TEST, 'Lancer le traitement en base de test')]
    institution = models.CharField(max_length=5,verbose_name=u"Code l'institution ",choices=INSTITUTION_CHOICES,default=UB)
    base = models.CharField(max_length=4,verbose_name=u"Choix du périmètre du traitement",choices=BASE_CHOICES,default=TEST)
    start_date = models.DateTimeField(auto_now_add=True, verbose_name=u"Date et heure de début du traitement")
    end_date = models.DateTimeField(auto_now_add=False, verbose_name=u"Date et heure de fin du traitement", null=True)
    is_done = models.BooleanField(default=False,verbose_name=u"Traitement terminé ?")
    num_title_to_processed = models.IntegerField(verbose_name=u"Nombre de titres à traiter")
    num_title_processed = models.IntegerField(verbose_name=u"Nombre de titres traités", default=0)
    file_upload = models.FileField(verbose_name=u"Fichier traité",upload_to='uploads/%Y/%m/%d/')
    file_download = models.FileField(verbose_name=u"Rapport de traitement", upload_to='downloads/%Y/%m/%d/')
    user = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            verbose_name=u"Responsable du traitement"
    )

    class Meta:
        verbose_name = "Traitement de modification en masse des exemplaires"
        verbose_name_plural = "Traitements de modification en masse des exemplaires"

    def link_file_download(self):
        if self.file_download : 
            return format_html(
                '<a href="{}">Télécharger le rapport de traitement</a>',
                self.file_download.url
            )
        else :
            return "-"
    link_file_download.short_description = "Rapport de traitement"
    