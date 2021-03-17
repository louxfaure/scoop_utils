# -*- coding: utf-8 -*-
import re
import os
import logging
import xml.etree.ElementTree as ET
from django.utils import timezone
import pytz
from django.template import loader
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.conf import settings
from pathlib import Path
from concurrent.futures.thread import ThreadPoolExecutor

from ..models import Process, Error
from .alma_to_sudoc import exist_in_sudoc
from .sudoc_to_alma import exist_in_alma

#Initialisation des logs
logger = logging.getLogger(__name__)


def handle_uploaded_file(f,process):
    types_analyses = {
        'ALMA_TO_SUDOC' : exist_in_sudoc,
        'SUDOC_TO_ALMA' : exist_in_alma
    }
    # logger.debug("lecture du fichier")
    # log_file = open("{}/static/sudoc/rapports/logs_{}_{}.txt".format(Path(__file__).resolve().parent,process.id,process.process_library.library_rcr), "w")
    with ThreadPoolExecutor(max_workers=5) as executor:
        num_line = 0
        for line in f :
            line = line.rstrip()
            if (clean_ppn = re.search("(^|\(PPN\))([0-9]{8}[0-9Xx]{1})(;|$)", line.decode())) is None :
                error = Error(  error_ppn = line.decode(),
                                error_type = 'PPN_MAL_FORMATE',
                                error_process = process)
                error.save()  
                logger.debug("{} - N'est pas un PPN valide ".format(line.decode()))
                # log_file.write("{}\t{}\t{}\n".format(num_line,line.decode(),"PPN mal formé"))
            else :
                ppn = clean_ppn.group(2)
                logger.debug("{} - Est un PPN valide ".format(ppn))
                executor.submit(types_analyses[process.process_job_type], num_line, ppn, process)
            
            if num_line%10 == 0 :
               process.process_num_title_processed = num_line
               process.save()

            num_line += 1
    logger.debug("Tous les Threads sont terminés  !!!")
    logger.debug("{}".format(settings.ADMINS[0][1]))
    process.process_is_done = True
    process.process_num_title_processed = num_line
    process.process_end_date = timezone.now()
    process.process_num_ppn_mal_formate = Error.objects.filter(error_process=process,error_type='PPN_MAL_FORMATE').count()
    process.process_num_ppn_inconnus_alma = Error.objects.filter(error_process=process,error_type='PPN_INCONNU_ALMA').count()
    process.process_num_ppn_inconnus_sudoc = Error.objects.filter(error_process=process,error_type='PPN_INCONNU_SUDOC').count()
    process.process_num_loc_inconnues_alma = Error.objects.filter(error_process=process,error_type='LOC_INCONNUE_ALMA').count()
    process.process_num_loc_inconnues_sudoc = Error.objects.filter(error_process=process,error_type='LOC_INCONNUE_SUDOC').count()
    process.process_num_doublons_notices_alma = Error.objects.filter(error_process=process,error_type='DOUBLON_ALMA').count()
    process.save()
    
    plain_message = loader.render_to_string("sudoc/end_process_message.txt", locals())
    user_email = EmailMessage(
        "L'analyse de recouvrement est terminée",
        plain_message,
        settings.ADMINS[0][1],
        [process.process_user.email],
    )
    user_email.send(fail_silently=False)
    logger.debug("mail envoyé  !!!")
    
    