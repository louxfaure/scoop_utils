# coding: utf-8
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
from itertools import product
import multiprocessing

from ..models import Process, Error
from .alma_to_sudoc import exist_in_sudoc
from .sudoc_to_alma import exist_in_alma

#Initialisation des logs
logger = logging.getLogger(__name__)

class MainProcess(object):
    def __init__(self, datas, process):
        self.datas = datas
        self.process = process
        logger.debug("{}".format(self.process.process_job_type))

    def run(self) :
        ids = [0, 1, 2, 3,4,5]
        manager = multiprocessing.Manager()
        idQueue = manager.Queue()
        for i in ids:
            idQueue.put(i)
        p = multiprocessing.Pool(8, self.init, (idQueue,))
        num_line = 0
        for result in p.imap(self.thread, self.datas):
            num_line += 1
            ppn, error_code, error_message = result
            logger.info("{}:{}:{}:{}\n".format(num_line,ppn, error_code,error_message))
            if error_code != 'OK' :
                error = Error(  error_ppn = ppn,
                    error_type = error_code,
                    error_message = error_message,
                    error_process = self.process)
                error.save()
            if num_line%100 == 0 :
                self.process.process_num_title_processed = num_line
                self.process.save()
        logger.info("Tous les Threads sont termines  !!!")
        logger.debug("{}".format(settings.ADMINS[0][1]))
        self.process.process_is_done = True
        self.process.process_num_title_processed = num_line
        self.process.process_end_date = timezone.now()
        self.process.process_num_ppn_mal_formate = Error.objects.filter(error_process=self.process,error_type='PPN_MAL_FORMATE').count()
        self.process.process_num_ppn_inconnus_alma = Error.objects.filter(error_process=self.process,error_type='PPN_INCONNU_ALMA').count()
        self.process.process_num_ppn_inconnus_sudoc = Error.objects.filter(error_process=self.process,error_type='PPN_INCONNU_SUDOC').count()
        self.process.process_num_loc_inconnues_alma = Error.objects.filter(error_process=self.process,error_type='LOC_INCONNUE_ALMA').count()
        self.process.process_num_loc_inconnues_sudoc = Error.objects.filter(error_process=self.process,error_type='LOC_INCONNUE_SUDOC').count()
        self.process.process_num_doublons_notices_alma = Error.objects.filter(error_process=self.process,error_type='DOUBLON_ALMA').count()
        self.process.process_num_erreurs_requetes = Error.objects.filter(error_process=self.process,error_type='ERREUR_REQUETE').count()
        self.process.save()
        
        plain_message = loader.render_to_string("sudoc/end_process_message.txt", locals())
        user_email = EmailMessage(
            "L'analyse de recouvrement est terminée",
            plain_message,
            settings.ADMINS[0][1],
            [self.process.process_user.email],
        )
        user_email.send(fail_silently=False)
        logger.debug("mail envoye !!!")


    def init(self,queue):
        global idx
        idx = queue.get()

    def thread(self,line):
        global idx
        types_analyses = {
            'ALMA_TO_SUDOC' : exist_in_sudoc,
            'SUDOC_TO_ALMA' : exist_in_alma
        }
        process_id = multiprocessing.current_process()
        logger.debug("{} - {} ".format(self.process.process_job_type,line.decode()))
        clean_ppn = re.search("(^|\(PPN\))([0-9]{8}[0-9Xx]{1})(;|$)", line.decode())
        if clean_ppn  is None :
            logger.debug("{} - N'est pas un PPN valide ".format(line.decode()))
            return(line.decode(),'PPN_MAL_FORMATE')
        else :
            ppn = clean_ppn.group(2)
            logger.debug("{} - Est un PPN valide ".format(ppn))
            return types_analyses[self.process.process_job_type](ppn, self.process)


    
    