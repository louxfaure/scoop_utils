# coding: utf-8
import re
import os
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
import time

from django.conf import settings

from ..models import Process, Error
# from .alma_to_sudoc import exist_in_sudoc
# from .sudoc_to_alma import exist_in_alma

#Initialisation des logs
logger = logging.getLogger(__name__)

def test_localisation(record,rcr):
    root = ET.fromstring(record)
    for library in root.findall(".//library"):
        if rcr == library.attrib['rcr'] :
            return True
    return False

def exist_in_sudoc(ppn,process):
    rcr = process.process_library.library_rcr
    logger.info("Thread {} début".format(ppn))
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    r = session.request(
        method='GET',
        headers= {
            "User-Agent": "outils_biblio/0.1.0",
            "Accept": "application/xml"
        },
        url= 'https://www.sudoc.fr/services/where/15/{}.xml'.format(ppn))
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("{} :: alma_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(ppn, r.status_code, r.request.method, r.url, r.text))
        # log_file.write("{}\t{}\t{}\n".format(num_line,ppn,"PPN inconnu"))
        # error = Error(  error_ppn = ppn,
        #         error_type = 'PPN_INCONNU_SUDOC',
        #         error_process = process)        
        # error.save() 
        return ppn, 'PPN_INCONNU_SUDOC'
    else:
        record = r.content.decode('utf-8')
        is_located = test_localisation(record,rcr)
        if is_located :
            # log_file.write("{}\t{}\t{}\n".format(num_line,ppn,"Localisé dans le SUDOC"))
            logger.debug("{} :: Existe".format(ppn))
            return ppn, 'OK'
        else :
            # log_file.write("{}\t{}\t{}\n".format(num_line,ppn,"Non localisé dans le SUDOC"))
            # error = Error(  error_ppn = ppn,
            #     error_type = 'LOC_INCONNUE_SUDOC',
            #     error_process = process)
            # error.save()
            return ppn, 'LOC_INCONNUE_SUDOC'  
            logger.debug("{} :: N'Existe pas".format(ppn))
    logger.info("Thread {} fin".format(ppn))