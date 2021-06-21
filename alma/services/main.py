# -*- coding: utf-8 -*-
import re
import os
import logging
import json
from django.utils import timezone
from chardet import detect
import csv
import datetime
from io import StringIO
from django.template import loader
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.core.files.base import ContentFile, File
from pathlib import Path
import multiprocessing


from .Alma_Apis import AlmaRecords
from ..models import ProcessUpdateItem

#Initialisation des logs
logger = logging.getLogger(__name__)

#Initialisation de l'API
logger = logging.getLogger(__name__)


# get file encoding type
def get_encoding_type(file):
    with open(file, 'rb') as f:
        rawdata = f.read()
    return detect(rawdata)['encoding']

def init(queue):
    global idx
    idx = queue.get()

def thread(x):
    global idx
    headers = x[0]
    api_key = x[1]
    barcode = x[2]
    process = multiprocessing.current_process()
    alma_api = AlmaRecords(apikey=api_key, region='EU', service=__name__)
    status,item = alma_api.get_item_with_barcode(barcode, accept='json')
    # logger.info("{}:{}:{}:{}:{}".format(x[1],x[2],x[3],x[4],x[5]))
    if status == "Error" :
        logger.error("{}:{}:{}:{}".format(idx,process.pid,barcode,item))
        return barcode,"Erreur",item
    else :
        logger.debug("{}:{}:{}:{}".format(idx,process.pid,barcode,item["item_data"]["barcode"]))
        i = 3
        bib_id = item["bib_data"]["mms_id"]
        holding_id = item["holding_data"]["holding_id"]
        item_id = item["item_data"]["pid"]
        for field in headers:
            item["item_data"][field] = x[i]
            i += 1
        status,reponse = alma_api.set_item(bib_id, holding_id, item_id, json.dumps(item), content_type='json', accept='json')
        if status == "Error" :
            logger.error("{}:{}:{}".format(os.getpid(),barcode,reponse))
            return barcode,"Erreur",reponse
        else :
            logger.info("{}:{}:{}:{}".format(os.getpid(),barcode,item["item_data"]["barcode"],reponse["item_data"]["barcode"]))
            return barcode, "Succés", "Exemplaire mis à jour"

def create_report_rep():
    download_rep = "{}/downloads".format(settings.MEDIA_ROOT)
    date = datetime.datetime.now()
    #Annee
    try:
        os.makedirs("{}/{}/".format(download_rep,date.year))
    except FileExistsError:
        # directory already exists
        pass
    #Mois
    try:
        os.makedirs("{}/{}/{}".format(download_rep,date.year,date.month))
    except FileExistsError:
        # directory already exists
        pass
    return "{}/{}/{}".format(download_rep,date.year,date.month)



def handle_uploaded_file(process):
    #Initilaisation de la clef d'API
    if process.base == 'TEST' :
        api_key = settings.ALMA_TEST_API_KEY[process.institution]
    else :
        api_key = settings.ALMA_API_KEY[process.institution]
    report_file = '/home/loux/Téléchargements/tmp/update-item_rapport_{}.csv'.format(process.id)
    # Lecture du fichier
    from_codec = get_encoding_type(process.file_upload.path)
    with open(process.file_upload.path, 'r', encoding=from_codec, newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        csv_data = csv.reader(csvfile, dialect)
        headers = next(csv_data)
        logger.info(headers)
        del headers[0]
        rows = []
        for row in csv_data:
            if len(row) < 2:
                continue
            row.insert(0, api_key)
            row.insert(0, headers)
            rows.append(row)
    logger.debug(__name__)
    # Prépartion et exécution des processus multimples
    ids = [0, 1, 2, 3,4,5]
    manager = multiprocessing.Manager()
    idQueue = manager.Queue()
    for i in ids:
        idQueue.put(i)
    p = multiprocessing.Pool(8, init, (idQueue,))
    num_line = 0
    report_array = []
    report_array.append("Code-barres\tStatut\tMessage")
    for result in p.imap(thread, rows):
        num_line += 1
        report_array.append("{}\t{}\t{}".format(*result))
        logger.info("{}:{}:{}:{}\n".format(num_line,*result))
        if num_line%100 == 0 :
            process.num_title_processed = num_line
            process.save()
    process.file_download = ContentFile("\n".join(report_array),"update-item_rapport_{}.csv".format(process.id))
    process.is_done = True
    process.num_title_processed = num_line
    process.end_date = timezone.now()
    process.save()
    plain_message = loader.render_to_string("alma/end_process_message.txt", locals())
    user_email = EmailMessage(
        "Le traitement des exemplaires est terminée",
        plain_message,
        settings.ADMINS[0][1],
        [process.user.email],
    )
    user_email.send(fail_silently=False)
    logger.debug("mail envoye !!!")
    logger.info("FIN DU TRAITEMENT")
