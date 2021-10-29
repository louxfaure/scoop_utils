# coding: utf-8
import os
import json
import logging
import xml.etree.ElementTree as ET
from django.http import response
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.conf import settings
from ..models import Process, Error

#Initialisation des logs 
logger = logging.getLogger(__name__)

ns = {'sru': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'diag':  'http://www.loc.gov/zing/srw/diagnostic/'}

def get_nb_result(reponsexml):
    """Retourne le nombre de résultats de la requête
    Args:
        reponsexml (xml obj): l'intégralité de la réponse à la reqête sru
    Returns:
        int: Nb de résultats
    """
    if reponsexml.findall("sru:numberOfRecords",ns):
        return int(reponsexml.find("sru:numberOfRecords",ns).text)
    else : 
        return 0

def test_loc(record,libraryId):
    """Teste si la bibliothèque "library_id" est localisée sous la notice
    Args:
        record ([xml obj]): noeud record
        libraryId ([type]): id alma de la bibliothèque

    Returns:
        string : "OK"" si bib localisée
    """
    for holding in record.findall(".//marc:datafield[@tag='AVA']",ns):
        if holding.find("marc:subfield[@code='b']",ns).text == libraryId :
            return "OK", "Bib. localisée"
    return "LOC_INCONNUE_ALMA", "Aucune localisation existe sous la notice pour la bibliothèque"

def test_other_system_id(record,ppn):
    for id in record.findall(".//marc:datafield[@tag='035']",ns):
        if id.find("marc:subfield[@code='a']",ns).text == "(PPN){}".format(ppn) :
            return True
    return False

def test_notices_mutiples(records,ppn,library_id):
    nb_ppn = 0
    for record in records.findall("sru:records/sru:record/sru:recordData/marc:record",ns):
        if test_other_system_id(record,ppn) :
            nb_ppn += 1
            response = test_loc(record,library_id)
    if nb_ppn == 1:
        return ppn, response
    elif nb_ppn > 1 :
        return ppn,("DOUBLON_ALMA", "Le sru remonte deux résultats pour le même ppn")
    else : 
        return ppn,("PPN_INCONNU_ALMA", "Le sru ne remonte aucun résultat pour le ppn")

# def test_erreur_sru(ppn,root) :


def test_localisation(ppn, record,library_id):
    logger.debug("test_loc pour {}".format(ppn))
    root = ET.fromstring(record)
    # Case 00968669 Le SRU retoune des erreures inexpliquées
    if root.find("sru:diagnostics/diag:diagnostic/diag:message",ns):
        return ppn,("ERREUR_REQUETE",root.find("sru:diagnostics/diag:diagnostic/diag:message",ns).text)
    nb_result = get_nb_result(root)
    logger.debug(nb_result)
    if nb_result == 0 :
        return ppn,("PPN_INCONNU_ALMA","Le sru ne remonte aucun résultat pour le ppn")
    elif nb_result > 1 :
        # Case 00968360 parfois Alma retourne plusieurs PPN il faut faire un test supplémentaire
        return test_notices_mutiples(root,ppn,library_id)
    else :
        return ppn,test_loc(root.find("sru:records/sru:record/sru:recordData/marc:record",ns),library_id)



def exist_in_alma(ppn,process):
    library_id = process.process_library.library_id
    institution = process.process_library.institution
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    url = "https://pudb-{}.alma.exlibrisgroup.com/view/sru/33PUDB_{}?version=1.2&operation=searchRetrieve&format=marcxml&query=alma.other_system_number=(PPN){}".format(institution.lower(),institution,ppn)
    logger.debug(url)

    r = session.request(
        method='GET',
        headers= {
            "User-Agent": "outils_biblio/0.1.0",
            "Accept": "application/xml"
        },
        url= url)
    try:
        r.raise_for_status()  
    except :
        logger.error("{} :: sudoc_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(
                                            ppn,
                                            r.status_code,
                                            r.request.method,
                                            r.url,
                                            r.text))
        return(ppn,("PPN_INCONNU_ALMA",r.text))
    return test_localisation(ppn, r.content.decode('utf-8'),library_id)