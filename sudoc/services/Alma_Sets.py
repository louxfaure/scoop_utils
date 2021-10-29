# -*- coding: utf-8 -*-
import os
# external imports
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import logging
import xml.etree.ElementTree as ET
import time
import sys
from math import *


__version__ = '0.1.0'
__api_version__ = 'v1'
__apikey__ = os.getenv('ALMA_API_KEY')
__region__ = os.getenv('ALMA_API_REGION')

ENDPOINTS = {
    'US': 'https://api-na.hosted.exlibrisgroup.com',
    'EU': 'https://api-eu.hosted.exlibrisgroup.com',
    'APAC': 'https://api-ap.hosted.exlibrisgroup.com'
}

FORMATS = {
    'json': 'application/json',
    'xml': 'application/xml'
}

RESOURCES = {
    'create_set' : 'conf/sets?combine=None&set1=None&set2=None',
    'update_set' : 'conf/sets/{set_id}?id_type={id_type}&op={op}',
    'retrieve_set' : 'conf/sets?q=name~{set_name}&limit=10&offset=0&set_origin=UI',
    'delete_set' : 'conf/sets/{set_id}'
}

class Set(object):
    """Intéragi avec des jeux  de résultats Alma"
    """

    def __init__(self, apikey=__apikey__):
        self.apikey = apikey
        self.endpoint = 'https://api-eu.hosted.exlibrisgroup.com'
        self.logger = logging.getLogger(__name__)
        
    @property
    #Construit la requête et met en forme les réponses
    def baseurl(self):
        """Construct base Url for Alma Api
        
        Returns:
            string -- Alma Base URL
        """
        return '{}/almaws/{}/'.format(self.endpoint, __api_version__)

    def fullurl(self, resource, ids={}):
        return self.baseurl + RESOURCES[resource].format(**ids)

    def headers(self, accept='json', content_type=None):
        headers = {
            "User-Agent": "pyalma/{}".format(__version__),
            "Authorization": "apikey {}".format(self.apikey),
            "Accept": FORMATS[accept]
        }
        if content_type is not None:
            headers['Content-Type'] = FORMATS[content_type]
        return headers
    def get_error_message(self, response, accept):
        """Extract error code & error message of an API response
        
        Arguments:
            response {object} -- API REsponse
        
        Returns:
            int -- error code
            str -- error message
        """
        error_code, error_message = '',''
        if accept == 'xml':
            root = ET.fromstring(response.text)
            error_message = root.find(".//xmlb:errorMessage",NS).text if root.find(".//xmlb:errorMessage",NS).text else response.text 
            error_code = root.find(".//xmlb:errorCode",NS).text if root.find(".//xmlb:errorCode",NS).text else '???'
        else :
            try :
             content = response.json()
            except : 
                # Parfois l'Api répond avec du xml même si l'en tête demande du Json cas des erreurs de clefs d'API 
                root = ET.fromstring(response.text)
                error_message = root.find(".//xmlb:errorMessage",NS).text if root.find(".//xmlb:errorMessage",NS).text else response.text 
                error_code = root.find(".//xmlb:errorCode",NS).text if root.find(".//xmlb:errorCode",NS).text else '???'
                return error_code, error_message 
            error_message = content['errorList']['error'][0]['errorMessage']
            error_code = content['errorList']['error'][0]['errorCode']
        return error_code, error_message
    
    def request(self, httpmethod, resource, ids, params={}, data=None,
                accept='json', content_type=None, nb_tries=0, in_url=None):
        #20190905 retry request 3 time s in case of requests.exceptions.ConnectionError
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        response = session.request(
            method=httpmethod,
            headers=self.headers(accept=accept, content_type=content_type),
            url= self.fullurl(resource, ids) if in_url is None else in_url,
            params=params,
            data=data)
        try:
            response.raise_for_status()  
        except requests.exceptions.HTTPError:
            self.logger.debug(response.text)
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.error("Alma_Apis :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            if error_code == '402263' :
                return 'Error_SetExist', "{} -- {}".format(error_code, error_message)
            return 'Error', "{} -- {}".format(error_code, error_message)
        except requests.exceptions.ConnectionError:
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.error("Alma_Apis :: Connection Error: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            return 'Error', "{} -- {}".format(error_code, error_message)
        except requests.exceptions.RequestException:
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.error("Alma_Apis :: Connection Error: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            return 'Error', "{} -- {}".format(error_code, error_message)
        return "Success", response

            

    
    def extract_content(self, response):
        ctype = response.headers['Content-Type']
        if 'json' in ctype:
            return response.json()
        else:
            return response.content.decode('utf-8')


    def create_set(self, set_name):
        data_dict = {
            "link": "",
            "name": set_name,
            "description": "Set créé par le programme d'analyse de synchronisation d'Alma avec le SUDOC",
            "type": {
                "value": "ITEMIZED"
            },
            "content": {
                "value": "BIB_MMS"
            },
            "private": {
                "value": "false"
            },
            "status": {
                "value": "ACTIVE"
            },
            "note": "",
            "query": {
                "value": ""
            },
            "members": {
                "total_record_count": "",
                "member": [
                
                ]
            },
            "origin": {
                "value": "UI"
            }
            }
        data =json.dumps(data_dict)
        status,response = self.request('POST', 'create_set',
                                {},
                                data=data, content_type = 'json', accept = 'json')
        if status == 'Error':
            return True, response
        elif status == 'Error_SetExist' :
            #Si un set existe avec le même Nom alam reetourne une erreur.
            ## On  var rechercher le set par son nom pour obtenir son ID
            ## On supprime le set
            ## Et on relance sa création
            status, reponse  = self.delete_set(set_name)
            if status == 'Error':
                return True, reponse
            status,response = self.request('POST', 'create_set',
                                {},
                                data=data, content_type = 'json', accept = 'json')
            if status == 'Error':
                return True, response
            self.logger.debug(response)
            return False, self.extract_content(response)
        else:
            return False, self.extract_content(response)
 
    def update_set(self,dataset,set_members,set_name) :
        self.logger.debug(json.dumps(dataset, indent=4))
        dataset['members']= {'member' : set_members} 
        self.logger.debug(json.dumps(dataset, indent=4))
        status,response = self.request('POST', 'update_set',
                                {   'set_id' : dataset['id'],
                                    'id_type' : 'SYSTEM_NUMBER',
                                    'op' : 'add_members',
                                    },
                                data=json.dumps(dataset), content_type = 'json', accept = 'json')
        if status == 'Error':
           
            return True, response
           
        else:
            return False, self.extract_content(response)        

    def get_set_id(self,set_name) :
        return self.request('GET', 'retrieve_set',
                                {   'set_name' : set_name,
                                    },
                                accept = 'json')

    
    def delete_set(self,set_name) :
        self.logger.debug("delete")
        error,reponse = self.get_set_id(set_name)
        self.logger.debug(self.extract_content(reponse))
        if error == "Error" :
            return error, reponse 
        result = self.extract_content(reponse)
        set_id = result["set"][0]["id"]
        self.logger.debug("set_id : {}".format(set_id))
        return self.request('DELETE', 'delete_set',
                                {   'set_id' : set_id,
                                    },
                                accept = 'json')
            
        
