from django.db import models
from django.contrib.auth.models import User
from django.utils.html import format_html



# Create your models here.
class Library(models.Model):
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
    library_name = models.CharField(max_length=200,verbose_name=u"Nom de la bibliotheque")
    library_id = models.CharField(max_length=10,verbose_name=u"Identifiant Alma de la bibliotheque",unique=True)
    library_rcr = models.CharField(max_length=10,verbose_name=u"RCR de la bibliotheque",unique=True)
    institution = models.CharField(max_length=5,verbose_name=u"Code l'institution ",choices=INSTITUTION_CHOICES,default=UB)

    def __str__(self):
        return str(self.library_name)
    
    class Meta:
        verbose_name = "Bibliothèque et RCR "
        verbose_name_plural = "Bibliothèques et RCR"

class Process(models.Model):
    ALMA_TO_SUDOC = 'ALMA_TO_SUDOC'
    SUDOC_TO_ALMA = 'SUDOC_TO_ALMA'
    JOB_TYPE_CHOICES = [    (ALMA_TO_SUDOC, 'Comparer les localisations Alma avec les localisations SUDOC'),
                            (SUDOC_TO_ALMA, 'Comparer les localisations SUDOC avec les localisations ALMA')]
    process_library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        verbose_name=u"Bibliothèque analysée"
    )
    process_start_date = models.DateTimeField(auto_now_add=True, verbose_name=u"Date et heure de début du traitement")
    process_end_date = models.DateTimeField(auto_now_add=False, verbose_name=u"Date et heure de fin du traitement", null=True)
    process_job_type = models.CharField(max_length=13,verbose_name=u"Analyse de recouvrement",choices=JOB_TYPE_CHOICES,default=ALMA_TO_SUDOC)
    process_is_done = models.BooleanField(default=False,verbose_name=u"Traitement terminé ?")
    process_num_title_to_processed = models.IntegerField(verbose_name=u"Nombre de titres à traiter")
    process_num_title_processed = models.IntegerField(verbose_name=u"Nombre de titres traités", default=0)
    process_num_ppn_mal_formate = models.IntegerField(verbose_name=u"Nombre de PPN erronnés", default=0)
    process_num_ppn_inconnus_alma = models.IntegerField(verbose_name=u"Nombre de PPN inconnus dans Alma", default=0)
    process_num_loc_inconnues_alma = models.IntegerField(verbose_name=u"Nombre de titres non localisés dans Alma", default=0)
    process_num_ppn_inconnus_sudoc = models.IntegerField(verbose_name=u"Nombre de PPN inconnus dans le SUDOC", default=0)
    process_num_loc_inconnues_sudoc = models.IntegerField(verbose_name=u"Nombre de titres non localisés dans le SUDOC", default=0)
    process_num_doublons_notices_alma = models.IntegerField(verbose_name=u"Nombre de doublons détectés dans Alma", default=0)
    process_user = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            verbose_name=u"Responsable du traitement"
    )

    def __str__(self):
        return str("{}-{}-{}".format(self.process_library.library_name,self.process_job_type,self.process_start_date ))

    class Meta:
        verbose_name = "Analyse de recouvrement"
        verbose_name_plural = "Analyses de recouvrement"

    def get_url(self, attr) :
        dict_error = {
            'process_num_ppn_mal_formate' : 'PPN_MAL_FORMATE',
            'process_num_ppn_inconnus_alma' : 'PPN_INCONNU_ALMA',
            'process_num_loc_inconnues_alma' : 'LOC_INCONNUE_ALMA',
            'process_num_ppn_inconnus_sudoc' : 'PPN_INCONNU_SUDOC',
            'process_num_loc_inconnues_sudoc' : 'LOC_INCONNUE_SUDOC',
            'process_num_doublons_notices_alma' : 'DOUBLON_ALMA'
        }
        if getattr(self,attr) > 0 :
            return format_html(
                '<a href="/admin/sudoc/error/?error_process__id__exact={}&error_type__exact={}&error_process__process_library__id__exact={}">{}</a>',
                self.id,
                dict_error[attr],
                self.process_library.id,
                getattr(self,attr),
                # sudoc/error/?error_process__id__exact=2&error_type__exact=PPN_INCONNU_SUDOC
            )
        else :
            return self.process_num_ppn_mal_formate 

    
    def link_process_num_ppn_mal_formate(self):
            return self.get_url('process_num_ppn_mal_formate')
    link_process_num_ppn_mal_formate.short_description = "Nombre de PPN erronnés"

    def link_process_num_ppn_inconnus_alma(self):
            return self.get_url('process_num_ppn_inconnus_alma')
    link_process_num_ppn_inconnus_alma.short_description = "Nombre de PPN inconnus dans Alma"

    def link_process_num_loc_inconnues_alma(self):
            return self.get_url('process_num_loc_inconnues_alma')
    link_process_num_loc_inconnues_alma.short_description = "Nombre de localisations inconnues dans Alma"

    def link_process_num_ppn_inconnus_sudoc(self):
            return self.get_url('process_num_ppn_inconnus_sudoc')
    link_process_num_ppn_inconnus_sudoc.short_description = "Nombre de PPN inconnus dans le SUDOC"

    def link_process_num_loc_inconnues_sudoc(self):
            return self.get_url('process_num_loc_inconnues_sudoc')
    link_process_num_loc_inconnues_sudoc.short_description = "Nombre de localisations inconnues dans le Sudoc"

    def link_process_num_doublons_notices_alma(self):
            return self.get_url('process_num_doublons_notices_alma')
    link_process_num_doublons_notices_alma.short_description = "Nombre de doublons détectés dans Alma"

class Error(models.Model):
    PPN_MAL_FORMATE = 'PPN_MAL_FORMATE'
    PPN_INCONNU_SUDOC = 'PPN_INCONNU_SUDOC'
    PPN_INCONNU_ALMA = 'PPN_INCONNU_ALMA'
    LOC_INCONNUE_SUDOC = 'LOC_INCONNUE_SUDOC'
    LOC_INCONNUE_ALMA = 'LOC_INCONNUE_ALMA'
    DOUBLON_ALMA = 'DOUBLON_ALMA'
    ERROR_TYPE_CHOICES = [  (PPN_INCONNU_SUDOC, 'PPN inconnu dans le SUDOC'),
                            (PPN_INCONNU_ALMA, 'PPN inconnu dans Alma'),
                            (LOC_INCONNUE_ALMA, 'Pas de localisation correspondante dans Alma'),
                            (LOC_INCONNUE_SUDOC, 'Pas de localisation correspondante dans le SUDOC'),
                            (PPN_MAL_FORMATE, 'PPN erronné'),
                            (DOUBLON_ALMA, 'Plusieurs notices avec le même PPN')]
    error_ppn = models.CharField(max_length=50,verbose_name=u"PPN")
    error_type = models.CharField(max_length=30,verbose_name=u"Anomalie",choices=ERROR_TYPE_CHOICES)
    error_process = models.ForeignKey(
            Process,
            on_delete=models.CASCADE,
            verbose_name=u"Traitement"
    )

    def __str__(self):
        return str("{} - {}".format(self.error_ppn, self.error_type ))

    class Meta:
        verbose_name = "Notice en anomalie"
        verbose_name_plural = "Notices en anomalies"