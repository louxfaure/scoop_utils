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
    'get_holding' : 'bibs/{bib_id}/holdings/{holding_id}',
    'get_holdings_list' : 'bibs/{bib_id}/holdings',
    'get_item_with_barcode' : 'items?item_barcode={barcode}',
    'get_item' : 'bibs/{bib_id}/holdings/{holding_id}/items/{item_id}',
    'get_set' : 'conf/sets/{set_id}',
    'get_set_members' : 'conf/sets/{set_id}/members?limit={limit}&offset={offset}'
}

NS = {'sru': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'xmlb' : 'http://com/exlibris/urm/general/xmlbeans'
         }

class AlmaRecords(object):
    """A set of function for interact with Alma Apis in area "Records & Inventory"
    """

    def __init__(self, apikey=__apikey__, region=__region__,service='AlmaPy'):
        if apikey is None:
            raise Exception("Please supply an API key")
        if region not in ENDPOINTS:
            msg = 'Invalid Region. Must be one of {}'.format(list(ENDPOINTS))
            raise Exception(msg)
        self.apikey = apikey
        self.endpoint = ENDPOINTS[region]
        self.service = service
        self.logger =  logging.getLogger(__name__)

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
            content = response.json()
            error_message = content['errorList'][0]['errorMessage']
            errorCode = content['errorList'][0]['errorCode']
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
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.warning("Alma_Apis :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            return 'Error', "{} -- {}".format(error_code, error_message)
        except requests.exceptions.ConnectionError:
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.warning("Alma_Apis :: Connection Error: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            return 'Error', "{} -- {}".format(error_code, error_message)
        except requests.exceptions.RequestException:
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.warning("Alma_Apis :: Connection Error: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            return 'Error', "{} -- {}".format(error_code, error_message)
        return "Success", response

            

    
    def extract_content(self, response):
        ctype = response.headers['Content-Type']
        if 'json' in ctype:
            return response.json()
        else:
            return response.content.decode('utf-8')


    #Retourne une holding à partir de son identifiant et de l'identifiant de la notice bib
    def get_holding(self, bib_id, holding_id, accept='xml'):
        status,response = self.request('GET', 'get_holding',
                                {'bib_id' : bib_id,
                                'holding_id' : holding_id},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)
    
    def get_holdings_list(self, bib_id, accept='xml'):
        status,response = self.request('GET', 'get_holdings_list',
                                {'bib_id' : bib_id},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)
    
    def set_holding(self, bib_id, holding_id, data):
        status, response = self.request('PUT', 'get_holding', 
                                {'bib_id': bib_id,'holding_id': holding_id},
                                data=data, content_type='xml', accept='xml')
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)

    def get_item_with_barcode(self,barcode, accept='xml'):
        status,response = self.request('GET', 'get_item_with_barcode',
                                {'barcode' : barcode},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)

    def get_item_with_url(self,in_url, accept='xml'):
        status,response = self.request('GET', None,
                                None,
                                in_url=in_url,
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)


    def set_item(self, bib_id, holding_id, item_id, data):

        status, response = self.request('PUT', 'get_item', 
                                {'bib_id': bib_id,
                                'holding_id': holding_id,
                                'item_id': item_id},
                                data=data, content_type='xml', accept='xml')
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)
    
    def get_set_members_list(self,set_id):
        members_list = []
        status, members_number = self.get_set_member_number(set_id)
        self.logger.debug(members_number)
        request_number = ceil(members_number/100)
        offset = 0
        for x in range(request_number):
            data = self.get_set_members(set_id, offset=offset)
            for member in data['member']:
                members_list.append(member['link'])
            offset = offset + 100

        return members_list

        #Retourne le nombre de membres d'un jeu de résultat
    def get_set_member_number(self, set_id, accept='json'):
        status, response = self.request('GET', 'get_set',
                                {'set_id': set_id},
                                accept=accept)
        if status == 'Error':
            self.logger.error(response)
            sys.exit()
        else:
            content = self.extract_content(response)
            members_num = content['number_of_members']['value']
            return status, members_num


    def get_set_members(self,set_id,limit=100,offset=0,accept='json'):
        status,response = self.request('GET', 'get_set_members',
                                {   'set_id' : set_id,
                                    'limit'  : limit,
                                    'offset' : offset,
                                },
                                accept=accept)
        if status == 'Error':
            self.logger.error(response)
            sys.exit()
        else:
            content = self.extract_content(response)
            return content
    

