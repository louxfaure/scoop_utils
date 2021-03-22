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

def test_localisation(record,library_id):
    root = ET.fromstring(record)
    num_result = int(root.attrib['total_record_count'])
    print (num_result)
    if num_result == 0 :
        return("error","PPN_INCONNU_ALMA")
    elif num_result > 1 :
        return("error","DOUBLON_ALMA") 
    else :
        if root.find("bib/record/datafield[@tag='AVA']/subfield[@code='b']") is not None :
            for alma_loc in root.findall ("bib/record/datafield[@tag='AVA']"):
                if alma_loc.find("subfield[@code='b']") is not None :
                    if alma_loc.find("subfield[@code='b']").text == library_id :
                        return("succes","LOC CONNUE ALMA")
        return("error","LOC_INCONNUE_ALMA")


def exist_in_alma(num_line,ppn,process):
    # library_id = '3100500000'
    # institution = 'UBM'
    library_id = process.process_library.library_id
    institution = process.process_library.institution
    api_key = settings.ALMA_API_KEY[institution]
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
    except requests.exceptions.HTTPError:
        logger.error("{} :: alma_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(
                                            ppn,
                                            r.status_code,
                                            r.request.method,
                                            r.url,
                                            r.text))
    # print (r.content)
    statut,code = test_localisation(r.content,library_id)
    if statut == "error" :
        error = Error(  error_ppn = ppn,
                        error_type = code,
                        error_process = process)
        error.save()  
    logger.debug("{} - {}".format(ppn,code))


    

