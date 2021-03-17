import re
import os
import logging
import requests
import threading
import xml.etree.ElementTree as ET
from .models import Process
from django.conf import settings
from pathlib import Path
import time

#Initialisation des logs
logger = logging.getLogger(__name__)

class WhereIs(threading.Thread):

    def __init__(self, ppn, rcr, num_line,log_file):
        threading.Thread.__init__(self)
        self.PPN = ppn
        self.RCR = rcr
        self.num_line = num_line
        self.log_file = log_file

    def run(self):
        url =  'https://www.sudoc.fr/services/where/15/{}.xml'.format(self.PPN)
        r = requests.get(url)
        try:
            r.raise_for_status()  
        except requests.exceptions.HTTPError:
            self.status = 'Error'
            # self.logger.error("{} :: XmlAbes_Init :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(ppn, r.status_code, r.request.method, r.url, r.text))
            self.log_file.write("{}\t{}\t{}\n".format(self.num_line,self.PPN,"PPN inconnu"))
            logger.debug("{} :: PPN inconnu ou service indisponible".format(self.PPN))
        else:
            self.record = r.content.decode('utf-8')
            is_located = self.test_rcr()
            if is_located :
                self.log_file.write("{}\t{}\t{}\n".format(self.num_line,self.PPN,"Localisé dans le SUDOC"))
                logger.debug("{} :: Existe".format(self.PPN))
            else :
                self.log_file.write("{}\t{}\t{}\n".format(self.num_line,self.PPN,"Non localisé dans le SUDOC"))
                logger.debug("{} :: N'Existe pas".format(self.PPN))

    
    def test_rcr(self):
        root = ET.fromstring(self.record)
        for library in root.findall(".//library"):
            rcr = library.attrib['rcr']
            if self.RCR == rcr :
                return True
        return False

def handle_uploaded_file(f,process):
    # Initialisation des compteurs
    num_ppn_badly_formatted = 0
    num_line = 1
    logger.debug("lecture du fichier")
    log_file = open("{}/static/sudoc/rapports/logs_{}_{}.txt".format(Path(__file__).resolve().parent,process.id,process.process_library.library_rcr), "w")
    for line in f :
        line = line.rstrip()
        if (clean_ppn := re.search("(^|\(PPN\))([0-9]{8}[0-9Xx]{1})(;|$)", line.decode())) is None :
            num_ppn_badly_formatted
            logger.debug("{} - N'est pas un PPN valide ".format(line.decode()))
            log_file.write("{}\t{}\t{}\n".format(num_line,line.decode(),"PPN mal formé"))
        else :
            ppn = clean_ppn.group(2)
            logger.debug("{} - Est un PPN valide ".format(ppn))
            traitement = WhereIs(ppn,process.process_library.library_rcr,num_line,log_file)
            traitement.start()
        num_line += 1
    while threading.activeCount() > 3:
        logger.debug("{}\n".format(threading.activeCount()))
        logger.debug(threading.enumerate())
        time.sleep(1)
    logger.debug("JOB TERMINE !!!")
    
    
    
    