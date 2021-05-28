# coding: utf-8
import os
import json
import logging
import xml.etree.ElementTree as ET
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.conf import settings
from ..models import Process, Error

#Initialisation des logs 
logger = logging.getLogger(__name__)

def test_localisation(record,library_id,ppn):
    root = ET.fromstring(record)
    num_result = int(root.attrib['total_record_count'])
    logger.debug(num_result)
    if num_result == 0 :
        return("error","PPN_INCONNU_ALMA")
    elif num_result > 1 :
        # CASE 00960223. l'api retrieve bibs retourne parfois de faux doublon sur un appel au PPN. On va donc tester tous les "Autres numéros système"
        match_ppn = 0
        loc_alma = 0
        for bib in root.findall ("bib"):
            for network_number in bib.findall("network_numbers"):
                if network_number.find("network_number") is not None :
                    if network_number.find("network_numbers").text == "(PPN){}".format(ppn) :
                        match_ppn =+ 1
                        if bib.find("bib/record/datafield[@tag='AVA']/subfield[@code='b']") is not None :
                            for alma_loc in bib.findall ("bib/record/datafield[@tag='AVA']"):
                                if alma_loc.find("subfield[@code='b']") is not None :
                                    if alma_loc.find("subfield[@code='b']").text == library_id :
                                        loc_alma =+ 1
                        continue
        if match_ppn > 1 :
            return("error","DOUBLON_ALMA")
        else :
            if loc_alma > 0 :
                return("succes","LOC CONNUE ALMA")
            else :
                return("error","LOC_INCONNUE_ALMA")
        return("error","DOUBLON_ALMA")
    else :
        if root.find("bib/record/datafield[@tag='AVA']/subfield[@code='b']") is not None :
            for alma_loc in root.findall ("bib/record/datafield[@tag='AVA']"):
                if alma_loc.find("subfield[@code='b']") is not None :
                    if alma_loc.find("subfield[@code='b']").text == library_id :
                        return("succes","LOC CONNUE ALMA")
        return("error","LOC_INCONNUE_ALMA")


def exist_in_alma(num_line,ppn,process):
    logger.debug('TRUC !!!!!!!!!!!!!!')
    library_id = process.process_library.library_id
    institution = process.process_library.institution
    api_key = settings.ALMA_API_KEY[institution]
    logger.debug('{}-->{}-{}-{}-{}'.format(ppn,process,library_id,institution,api_key))
    # api_key = os.getenv("TEST_UBM_API")
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    r = session.request(
        method='GET',
        headers= {
            "User-Agent": "outils_biblio/0.1.0",
            "Authorization": "apikey {}".format(api_key),
            "Accept": "application/xml"
        },
        url= "https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs?view=full&expand=p_avail&other_system_id=(PPN){}".format(ppn))
    try:
        r.raise_for_status()  
    except :
        logger.error("{} :: alma_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(
                                            ppn,
                                            r.status_code,
                                            r.request.method,
                                            r.url,
                                            r.text))
    statut,code = test_localisation(r.content,library_id,ppn)
    if statut == "error" :
        error = Error(  error_ppn = ppn,
                        error_type = code,
                        error_process = process)
        error.save()  
    logger.info("{} - {}".format(ppn,code))