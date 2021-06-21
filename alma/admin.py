from django.contrib import admin
from django.http import HttpResponse,HttpResponseRedirect
from django.conf.urls import url
from django.urls import path
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from .models import ProcessUpdateItem
from .forms import UploadFileForm
from .services import main
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
class LibraryAdmin(admin.ModelAdmin):
    list_display = ('id','file_upload', 'institution', 'base', 'start_date','num_title_to_processed', 'is_done','num_title_processed')
    ordering = ('start_date',)
    search_fields = ('file_upload',)
   
    def get_urls(self):

        # get the default urls
        urls = super(LibraryAdmin, self).get_urls()

        # define security urls
        security_urls = [
            path('add/', self.admin_site.admin_view(self.execute_process)),
            # Add here more urls if you want following same logic
        ]

        # Make sure here you place your added urls first than the admin default urls
        return security_urls + urls

    def execute_process(self,request):
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                if form.cleaned_data['base'] == 'TEST' and form.cleaned_data['institution'] in ('INP','IEP'):
                    messages.error(request,'Nous ne disposons pas de bac à sable pour l''institution {}'.format(form.cleaned_data['institution']))
                    return HttpResponseRedirect("/admin/alma/processupdateitem/add")
                user = request.user
                process = ProcessUpdateItem( institution = form.cleaned_data['institution'],
                                base = form.cleaned_data['base'],
                                file_upload = request.FILES['file'],
                                user = user,
                                num_title_to_processed = sum(1 for line in request.FILES['file']) - 1
                            )         
                process.save()
                logger.info("Process cree")            
                ExecuteJobThread(process).start()
                # request.session['pid'] = process.id
                messages.success(request, 'L''analyse a été lancée . Vous recevrez un meessage sur {} à la fin du traitement'.format( user.email))
                return HttpResponseRedirect("/admin/alma/processupdateitem/")
        else:
            form = UploadFileForm()
        return render(request, "sudoc/execute-process.html", locals())
