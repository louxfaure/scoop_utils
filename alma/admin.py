from django.contrib import admin
from django.http import HttpResponse,HttpResponseRedirect
from django.conf.urls import url
from django.urls import path
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.conf import settings
from .models import ProcessUpdateItem
from .forms import UploadFileForm
from .services import main, Alma_Apis
import logging
import threading

# Register your models here.

#Initialisation des logs
logger = logging.getLogger(__name__)

#Thread pour le lancement du traitement
class ExecuteJobThread(threading.Thread):

    def __init__(self,process):
        self.process = process
        threading.Thread.__init__(self)

    def run(self):
        logger.debug("Lancement du traitement ExecuteJobThread")
        main.handle_uploaded_file(self.process)
        logger.debug("Fin ExecuteJobThread")


@admin.register(ProcessUpdateItem)
class UpdateItemProcesss(admin.ModelAdmin):
    list_display = ('id', 'institution', 'base', 'start_date', 'end_date','num_title_to_processed', 'is_done','num_title_processed','link_file_download')
    ordering = ('start_date',)
    search_fields = ('file_upload',)


   
    def get_urls(self):
        """ Surcharge les urls pour le modèle
        """

        # get the default urls
        urls = super(UpdateItemProcesss, self).get_urls()

        # define security urls
        security_urls = [
            path('add/', self.admin_site.admin_view(self.execute_process)),
            # Add here more urls if you want following same logic
        ]

        # Make sure here you place your added urls first than the admin default urls
        return security_urls + urls

    def execute_process(self,request):
        # vue pour le formulaire de lancement du processus de traitement des exemplaires
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                # Teste s'il reste suffisamment d'appels d'Api autorisés pour lancer le traitement sur toutes les lignes du fichier
                alma_api = Alma_Apis.AlmaRecords(apikey=settings.ALMA_API_KEY[form.cleaned_data['institution']], region='EU', service=__name__)
                status,nb_api_call = alma_api.get_api_remaining()
                if status == "Error" :
                    # Pb. de clef où indisponibilité du service
                    messages.error(request,"L'API Alma remonte l'erreur suivante :  {}".format(nb_api_call))
                    return HttpResponseRedirect("/admin/alma/processupdateitem/add")
                num_ligne = sum(1 for line in request.FILES['file']) - 1
                if (num_ligne*3) > (int(nb_api_call) - 10000) :
                    messages.error(request,"Nous ne disposons que de {} appels d'API pour la journée. Votre fichier contient {} lignes. Il faut deux appels par ligne pour traiter le fichier. Merci de diminuer le nombre de lignes à traiter".format(nb_api_call,num_ligne))
                    return HttpResponseRedirect("/admin/alma/processupdateitem/add")
                # Teste si institution possède bien une base de test
                if form.cleaned_data['base'] == 'TEST' and form.cleaned_data['institution'] in ('INP','IEP'):
                    messages.error(request,'Nous ne disposons pas de bac à sable pour l''institution {}'.format(form.cleaned_data['institution']))
                    return HttpResponseRedirect("/admin/alma/processupdateitem/add")
                # Teste si un autre process est en cours 
                if ProcessUpdateItem.objects.filter(is_done=False).count() > 0 :
                    messages.error(request,'Un autre processus est en cours attendez la fin de son exécution pour lancer un nouveau traitement')
                    return HttpResponseRedirect("/admin/alma/processupdateitem")
                
                user = request.user
                process = ProcessUpdateItem( institution = form.cleaned_data['institution'],
                                base = form.cleaned_data['base'],
                                file_upload = request.FILES['file'],
                                user = user,
                                num_title_to_processed = num_ligne
                            )         
                process.save()
                logger.info("Process cree")            
                ExecuteJobThread(process).start()
                # request.session['pid'] = process.id
                messages.success(request, 'L''analyse a été lancée . Vous recevrez un meessage sur {} à la fin du traitement'.format( user.email))
                return HttpResponseRedirect("/admin/alma/processupdateitem/")
        else:
            form = UploadFileForm()
        return render(request, "alma/execute-process.html", locals())
