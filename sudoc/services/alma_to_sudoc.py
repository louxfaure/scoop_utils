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

#Initialisation des logs
logger = logging.getLogger(__name__)

def test_localisation(librairies,rcr):
    for library in librairies:
        if rcr == library.attrib['rcr'] :
            return True
    return False

def exist_in_sudoc(ppns_list,process):
    """Teste pour une liste de PPN et un RCR données si une localisation existe dans le SUDOC

    Args:
        ppns_list (array): liste de ppn
        process (objec): traitement pour lequel la liste doit être traitée conctient le rcr process.process_library.library_rcr
    """
 
    rcr = process.process_library.library_rcr
    logger.info("Thread {} début".format(ppns_list))
    # Préparation et envoie de la requête à l'ABES
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
        url= 'https://www.sudoc.fr/services/where/15/{}.xml'.format(','.join(ppns_list)))
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("{} :: alma_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(','.join(ppns_list), r.status_code, r.request.method, r.url, r.text))
        # Si le service ne répond pas pour la requête on créé une erreur pour chaque PPN
        for ppn in ppns_list :
            error = Error(  error_ppn = ppn,
                    error_type = 'ERREUR_REQUETE',
                    error_process = process)        
            error.save() 
    #Traitement des résultats
    else:
        ppns_requetes = [] 
        ppns_connus =[] #Liste des ppns retrouvés par le web service
        results = r.content.decode('utf-8')
        root = ET.fromstring(results)
        #Pour chaque résultat 
        for result in root.findall(".//result"):
            # On récupère le PPN nettoyé
            ppn = result.attrib['ppn']
            # On l'ajoute à la liste des ppns retrouvés par le web service
            ppns_connus.append(ppn)
            # On regarde si une localisation existe pour le PPN 
            is_located = test_localisation(result.findall(".//library"),rcr)
            if is_located :
                logger.debug("{} :: Existe".format(ppn))
            else :
                error = Error(  error_ppn = ppn,
                    error_type = 'LOC_INCONNUE_SUDOC',
                    error_process = process)
                error.save()
                logger.debug("{} :: N'Existe pas".format(ppn))
        # On identifie les ppns inconnus du SUDOC
