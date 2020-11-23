from django.db import models
from django.utils import timezone
from datetime import datetime
from django.contrib.auth.models import User

# from django.utils.safestring import SafeString


# Create your models here.
class Person(models.Model):
    id_alma =  models.CharField(max_length=254,primary_key=True,verbose_name=u"Primary id")
    barcode = models.CharField(max_length=20,verbose_name=u"Code-barres")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(verbose_name=u"Adresse mail du lecteur")

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)

    class Meta:
        verbose_name = "Lecteur"
        verbose_name_plural = "Lecteurs"

    @property
    def full_name(self):
        "Returns the person's full name."
        return '%s %s' % (self.first_name, self.last_name)

class DaysOfWeek(models.Model):
    day_no = models.IntegerField()
    day = models.CharField(max_length=8)

    def __str__(self):
        return self.day

    class Meta:
        verbose_name = "Jour"
        verbose_name_plural = "Jours d'ouvertures"


class ClosedDays(models.Model):
    date = models.DateField(verbose_name=u"Date de fermetures de la bibliothèque")

    def __str__(self):
        return self.date.strftime('%d/%m/%Y')
    

    class Meta:
        verbose_name = "Jour"
        verbose_name_plural = "Jours de fermetures"

class PickupLocation(models.Model):
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
    id_alma =  models.CharField(max_length=10,primary_key=True,verbose_name=u"Identifiant Alma")
    name = models.CharField(max_length=200,verbose_name=u"Nom de la bibliotheque")
    institution = models.CharField(max_length=5,verbose_name=u"Code l'institution ",choices=INSTITUTION_CHOICES,default=UB)
    plot_number = models.IntegerField(verbose_name=u"Nombre de plages par heure",default=4)
    handling_time = models.IntegerField(verbose_name=u"Délai en jour pour la préparation de la commande",default=1)
    handling_time_external_library = models.IntegerField(verbose_name=u"Délai en jours pour la préparation de la commande quand le document vient d'une autre bibliothèque",default=7)
    open_hour = models.IntegerField(verbose_name=u"Heure d'ouverture du service de retrait",default=9)
    close_hour = models.IntegerField(verbose_name=u"Heure de fermeture du service de retrait",default=17)
    opening_days = models.ManyToManyField(DaysOfWeek)
    closed_days = models.ManyToManyField(ClosedDays,blank=True)
    mid_day_break = models.BooleanField(default=False,verbose_name=u"Fermeture méridienne (bibliothèque fermée entre 12h & 14h)")
    days_for_booking = models.IntegerField(verbose_name=u"Nombre de jours à proposer pour la prise de rdv",default=10)
    email = models.EmailField(verbose_name=u"Adresse vers laquelle envoyer la liste des documents réservés",default="")
    from_email = models.EmailField(verbose_name=u"Adresse à utiliser pour l'envoi du mail au lecteur",default="")
    tel = models.CharField(max_length=50,verbose_name=u"Téléphone",blank=True,default='00 00 00 00 00')
    url = models.URLField(verbose_name=u"Lien vers les informations d'accès à la bibliothèque",blank=True,default='')
    message = models.CharField(max_length=500,verbose_name=u"Message",blank=True,default='')
    lat = models.CharField(max_length=50,verbose_name=u"Latitude",blank=True,default='')
    longitude = models.CharField(max_length=50,verbose_name=u"Longitude",blank=True,default='')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Bibliothèque de retrait"
        verbose_name_plural = "Bibliothèques de retrait"

    def get_opening_days(self):
        return ",".join([str(p) for p in self.opening_days.all()])
    get_opening_days.short_description = u'Jours d\'ouverture'


class Appointment(models.Model):
    date =  models.DateTimeField(verbose_name=u"Date de retrait des ouvrages")
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        verbose_name=u"Lecteur",
        related_name="person"
    )
    library = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        verbose_name=u"Bibliothèque de retrait"
    )
    is_done = models.BooleanField(default=False,verbose_name=u"Commande retirée ?")
    is_peb = models.BooleanField(default=False,verbose_name=u"Demande de PEB ?")
    peb_descr = models.CharField(max_length=500,verbose_name=u"Descriptif PEB :",blank=True,default='')
    class Meta:
        unique_together = (('date', 'library'),)
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ['date']
    
    def __str__(self):
        return self.date.strftime('%d/%m/%Y à %HH%M')
   
    def get_date_in_date_time(self):
        return datetime.strptime(self.date[0:19], '%Y-%m-%d %H:%M:%S')
        return self.date

    def get_date_formatee(self,format):
        formats_list = {
            'alma' : '%Y-%m-%dZ',
            'jour' : '%d/%m/%Y',
            'heure' : '%HH%M',
            'complet' : '%d/%m/%Y à %HH%M'

        }
        date_to_return = self.get_date_in_date_time()
        return date_to_return.strftime(formats_list[format])

    def get_number_of_items(self):
        if self.is_peb :
            return "PEB"
        else :
            return Items.objects.filter(appointment=self).count()
    get_number_of_items.short_description = u'Nombre de documents'


    # def get_number_of_canceled_items(self):
    #     return Items.objects.filter(appointment=self).filter(get_item_status='IN_PROCESS').count()
    # get_number_of_canceled_items.short_description = u'Nombre de documennts annulés'

class Items(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name=u"Date et heure de création")
    modified = models.DateTimeField(auto_now=True,verbose_name=u"Date et heure de modification")
    user_request_id =  models.CharField(max_length=16,primary_key=True,verbose_name=u"Identifiant de la réservation")
    title = models.CharField(max_length=500,verbose_name=u"Titre de l'exemplaire")
    item_barcode = models.CharField(max_length=30,verbose_name=u"Code-barres",blank=True, null=True)
    library_name = models.CharField(max_length=200,verbose_name=u"Nom de la bibliotheque")
    library_id = models.CharField(max_length=10,verbose_name=u"Identifiant Alma de la bibliotheque",blank=True, null=True)
    location = models.CharField(max_length=200,verbose_name=u"Localisation de l'exemplaire",blank=True, null=True)
    call_number = models.CharField(max_length=30,verbose_name=u"Cote de l'exemplaire",blank=True, null=True)
    description = models.CharField(max_length=300,verbose_name=u"Description du fascicule (système)",blank=True, null=True)
    manual_description = models.CharField(max_length=300,verbose_name=u"Description du fascicule (usager)",blank=True, null=True)
    status = models.CharField(max_length=80,verbose_name=u"Statut de la réservation",blank=True, null=True)
    person = models.ForeignKey(
        Person,
        verbose_name=u"Demandeur",
        on_delete=models.CASCADE,
    )
    pickuplocation = models.ForeignKey(
        PickupLocation,
        verbose_name=u"Bibliothèque de retrait",
        on_delete=models.CASCADE,
    )
    appointment = models.ForeignKey(
        Appointment,
        models.SET_NULL,
        blank=True,
        null=True,
    )


    def __str__(self):
        return str(self.user_request_id)

    class Meta:
        verbose_name = "Document réservé"
        verbose_name_plural = "Documents réservés"

    def get_item_status(self):
        from .services import services_request

        return services_request.get_request_user_status(self.person.id_alma,self.user_request_id,self.pickuplocation.institution)


# Comptes admin ajout d'un champ
class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    library = models.ForeignKey(
        PickupLocation,
        on_delete=models.CASCADE,
        verbose_name=u"Bibliothèque"
    )

