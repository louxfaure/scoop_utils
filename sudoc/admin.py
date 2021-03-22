from django.contrib import admin
from django.http import HttpResponse,HttpResponseRedirect
from django.conf.urls import url
from django.urls import path
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Library, Process, Error
from .forms import UploadFileForm
from .services import main
import csv
import logging
import threading
# Register your models here.

#Initialisation des logs
logger = logging.getLogger(__name__)

#Thread pour le lancement du traitement
class ExecuteJobThread(threading.Thread):

    def __init__(self,upload_file,process):
        self.upload_file = upload_file
        self.process = process
        threading.Thread.__init__(self)

    def run(self):
        logger.debug("Lancement du traitement ExecuteJobThread")
        main.handle_uploaded_file(self.upload_file,self.process)
        logger.debug("Ending ExecuteJobThread")

# EXport en CSV
class ExportMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Exporter en CSV"

    def export_as_set(self, request, queryset):
        print(queryset)
        for obj in queryset:
            print(obj.error_ppn)

        # meta = self.model._meta
        # field_names = [field.name for field in meta.fields]

        # response = HttpResponse(content_type='text/csv')
        # response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        # writer = csv.writer(response)

        # writer.writerow(field_names)
        # for obj in queryset:
        #     row = writer.writerow([getattr(obj, field) for field in field_names])

        # return response

    export_as_set.short_description = "Créer un jeu de résultat Alma"


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin,ExportMixin):
    list_display = ('library_id', 'library_rcr', 'library_name', 'institution')
    ordering = ('library_name', 'institution')
    search_fields = ('library_id', 'library_rcr', 'library_name')
    actions = ["export_as_csv"]

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('process_library',
                    'process_job_type',
                    'process_is_done', 
                    'process_start_date',
                    'process_end_date',
                    'process_num_title_to_processed', 
                    'process_num_title_processed',
                    'link_process_num_ppn_mal_formate',
                    'link_process_num_ppn_inconnus_alma',
                    'link_process_num_loc_inconnues_alma',
                    'link_process_num_ppn_inconnus_sudoc',
                    'link_process_num_loc_inconnues_sudoc')
    ordering = ('process_start_date', 'process_library')
    list_filter = ['process_library','process_job_type', 'process_start_date']
    search_fields = ('process_library', 'process_job_type', 'process_start_date','process_is_done','id')


    
    def get_urls(self):

        # get the default urls
        urls = super(ProcessAdmin, self).get_urls()

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
                user = request.user
                library = Library.objects.get(library_name=form.cleaned_data['library'])
                nb_of_line = sum(1 for line in request.FILES['file'])
                process = Process( process_library = library,
                                process_num_title_to_processed = nb_of_line,
                                process_user = user,
                                process_job_type = form.cleaned_data['job_type']
                            )         
                process.save()
                logger.info("Process cree")            
                ExecuteJobThread(request.FILES['file'],process).start()
                request.session['pid'] = process.id
                messages.success(request, 'L''analyse de recouvrement a été lancée pour la bibliothèque {}. Vous recevrez un meessage sur {} à la fin du traitement'.format(library, user.email))
                return HttpResponseRedirect("/admin/sudoc/process/")

        else:
            form = UploadFileForm()
        return render(request, "sudoc/execute-process.html", locals())

@admin.register(Error)
class ErrorAdmin(admin.ModelAdmin, ExportMixin):
    list_display = ('error_ppn', 'error_type', 'error_process')
    ordering = ('error_process','error_type')
    list_filter = ['error_process__process_library','error_type','error_process__process_job_type']
    search_fields = ('error_ppn', 'error_type', 'error_process')
    actions = ["export_as_csv"]