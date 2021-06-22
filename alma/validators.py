from django.core.exceptions import ValidationError
import mimetypes
import csv
import logging
from io import StringIO
import requests
from urllib.error import HTTPError
import xml.etree.ElementTree as ET
#Initialisation des logs
logger = logging.getLogger(__name__)

ITEM_XSD = 'https://developers.exlibrisgroup.com/wp-content/uploads/alma/xsd/rest_item.xsd'
XSD = {'xs': 'http://www.w3.org/2001/XMLSchema'}

def csv_content_validator(csv_upload):
    """Valide le fichier csv :
            -- Teste l'extention
            -- Tesste les délimitateurs
            -- Regarde si les collonnes sont bien des champs exemplaires Alma éditable via API
    Args:
        csv_upload ([type]): [description]

    Raises:
        ValidationError: [description]
    """
    # Teste l'extention du fichier
    if not csv_upload.name.endswith(('.csv','.txt','tsv')) :
        raise ValidationError('Le fichier doit être un fichier csv, txt ou tsv')
    # Teste le délimitateur utilisé
    file = csv_upload.read().decode('utf-8')
    csv_file = StringIO(file)
    dialect = csv.Sniffer().sniff(csv_file.read(1024))
    logger.debug(dialect)
    if dialect.delimiter not in (';','\t',','):
        raise ValidationError('Le délimitateur doit être doit être une virgule, un point virgule ou une tabulation.')
    # Teste si la première colonne est bien un code-barres
    csv_data = csv.reader(StringIO(file), dialect)
    headers = next(csv_data)
    logger.info(headers)
    if headers[0] != 'barcode' :
        raise ValidationError('La première colonne de votre fichier doit être intitulée "barcode" et comporter les codes-barres des exemplaires à modifier')
    #Teste si les colonnes pointe vers des champs exemplaires Alma éditable via API 
    del headers[0]
    r = requests.get(ITEM_XSD)
    try:
        r.raise_for_status()  
    except requests.exceptions.HTTPError:
        raise HTTPError(r,__name__)
    reponse = r.content.decode('utf-8')
    reponsexml = ET.fromstring(reponse)
    item_data = reponsexml.find("xs:complexType[@name='item_data']/xs:all",XSD)
    for field in headers:
        if item_data.find("xs:element[@name='{}']".format(field),XSD):
            if (item_data.find("xs:element[@name='{}']/xs:annotation/xs:appinfo/xs:tags".format(field),XSD).text == 'api get post put') :
                logger.info("Le champ {} peut bien être modifié par API".format(field))
            else :
                raise ValidationError('Erreur nommage colonne : {} n''est pas un champ autorisé à l''écriture dans Alma'.format(field))
            # return reponsexml.find("sru:numberOfRecords",ns).text
        else :
            raise ValidationError('Erreur nommage colonne : Le champ {} n''est pas un champ exemplaire connu dans Alma'.format(field)) 
    logger.info("Test du nomage des champs terminé")

