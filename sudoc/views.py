from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import Library, Process
from .forms import UploadFileForm
from .services import main
import requests
import xml.etree.ElementTree as ET
import logging
import threading
# import os

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


@login_required(login_url='/admin/login/')
def home(request):
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
            logger.info("Process créé")            
            ExecuteJobThread(request.FILES['file'],process).start()
            request.session['pid'] = process.id
            return HttpResponseRedirect(reverse('success'))
    else:
        form = UploadFileForm()
    return render(request, "sudoc/home.html", locals())

def success(request):
    process = Process.objects.get(id=request.session.get('pid'))
    return render(request, "sudoc/success.html", locals())