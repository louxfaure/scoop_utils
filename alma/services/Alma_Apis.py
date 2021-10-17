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
    'get_holding' : 'bibs/{bib_id}/holdings/{holding_id}',
    'get_holdings_list' : 'bibs/{bib_id}/holdings',
    'get_item_with_barcode' : 'items?item_barcode={barcode}',
    'get_item' : 'bibs/{bib_id}/holdings/{holding_id}/items/{item_id}',
    'get_set' : 'conf/sets/{set_id}',
    'get_set_members' : 'conf/sets/{set_id}/members?limit={limit}&offset={offset}',
    'get_record' : 'bibs/{mms_id}?view={view}&expand={expand}',
    'retrieve_record' : 'bibs?{id_type}={bib_id}&view={view}&expand={expand}',
    'update_record' : 'bibs/{bib_id}',
    'get_item_requests_list' : 'bibs/{bib_id}/holdings/{holding_id}/items/{item_id}/requests?request_type={request_type}&status={status}',
    'delete_request' : 'bibs/{bib_id}/holdings/{holding_id}/items/{item_id}/requests/{request_id}?reason={reason}&notify_user={notify_user}',
    'ending_process' : 'bibs/{bib_id}/holdings/{holding_id}/items/{item_id}?op=scan&library={library_code}&department={department}&done=true',
    'test' : 'bibs/test'
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
        self.logger = logging.getLogger(service)

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
            if response.status_code == 400 :
                return 'Error', "{} -- {}".format(400, response)
            else :
                error_code, error_message= self.get_error_message(response,accept)
            if error_code == "401873" :
                return 'Error', "{} -- {}".format(error_code, "Notice innconnue")
            self.logger.error("Alma_Apis :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
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


    def set_item(self, bib_id, holding_id, item_id, data, content_type='xml', accept='xml'):

        status, response = self.request('PUT', 'get_item', 
                                {'bib_id': bib_id,
                                'holding_id': holding_id,
                                'item_id': item_id},
                                data=data, content_type = content_type, accept = accept)
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

    def get_record(self,mms_id,view='full',expand='None',accept='xml'):
        """Return a bibliographic record with a mms_id

        Args:
            mms_id ([type]): [description]
            view (str, optional): Use view=brief to retrieve without the full record. Use view=local_fields to retrieve only local fields for an IZ record linked to an NZ record.. Defaults to 'full'.
            expand (str, optional): This parameter allows for expanding the bibliographic record with additional information. To use more than one, use a comma separator.. Defaults to 'None'.
            accept (str, optional): [description]. Defaults to 'xml'.

        Returns:
            [type]: [description]
        """
        status,response = self.request('GET', 'get_record',
                                {   'mms_id' : mms_id,
                                    'view'  : view,
                                    'expand' : expand,
                                },
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)
   
    def retrieve_record(self,id_type,bib_id,view='full',expand='None',accept='xml'):
        """This web service returns Bib records in an XML format from a list of Bib IDs (mms_id, nz_mms_id, ie_id, cz_mms_id, other_system_id, 
        Ie Id, holdings_id, representation_id) submitted in a parameter.

        Args:
            id_type (string) : mms_id, nz_mms_id, ie_id, cz_mms_id, other_system_id, Ie Id, holdings_id, representation_id
            bib_id (int): identifier
            view (str, optional): Use view=brief to retrieve without the full record. Use view=local_fields to retrieve only local fields for an IZ record linked to an NZ record.. Defaults to 'full'.
            expand (str, optional): This parameter allows for expanding the bibliographic record with additional information. To use more than one, use a comma separator.. Defaults to 'None'.
            accept (str, optional): [description]. Defaults to 'xml'.

        Returns:
            [type]: [description]
        """
        status,response = self.request('GET', 'retrieve_record',
                                {   'id_type' : id_type,
                                    'bib_id' : bib_id,
                                    'view'  : view,
                                    'expand' : expand,
                                },
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)

    def update_record(self, bib_id, data):
        """Update a bibliographic record with xml data passed in parameter

        Args:
            bib_id (string): [description]
            data (xml): [description]

        Returns:
            staus: Sucess ou ERROR
            response: Upadtaed Record or Error message
        """

        status, response = self.request('PUT', 'update_record', 
                                {'bib_id': bib_id},
                                data=data, content_type='xml', accept='xml')
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)
    
    def get_item_requests_list(self, bib_id, holding_id, item_id, request_type ,status='active',accept='json'):
        """Listtes les requêtes passées sur un item

        Args:
            bib_id ([type]): [description]
            holding_id ([type]): [description]
            item_id ([type]): [description]
            request_type ([type]): [description]
            status (str, optional): [description]. Defaults to 'active'.
            accept (str, optional): [description]. Defaults to 'json'.

        Returns:
            [type]: [description]
        """
        status, response = self.request('GET', 'get_item_requests_list', 
                                {'bib_id': bib_id,
                                'holding_id': holding_id,
                                'item_id': item_id,
                                'request_type' : request_type,
                                'status' : status},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)

    def delete_request(self, bib_id, holding_id, item_id, request_id ,reason='CannotBeFulfilled',notify_user='false',accept='json'):
        """[summary]

        Args:
            bib_id ([type]): [description]
            holding_id ([type]): [description]
            item_id ([type]): [description]
            request_id ([type]): [description]
            reason (str, optional): [description]. Defaults to 'CannotBeFulfilled'.
            notify_user (str, optional): [description]. Defaults to 'false'.
            accept (str, optional): [description]. Defaults to 'json'.

        Returns:
            [type]: [description]
        """
        status, response = self.request('DELETE', 'delete_request', 
                                {'bib_id': bib_id,
                                'holding_id': holding_id,
                                'item_id': item_id,
                                'request_id' :request_id,
                                'reason' : reason,
                                'notify_user' : notify_user},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, response

    def ending_process (self, bib_id, holding_id, item_id, library_code, department ,accept='json'):
        status, response = self.request('POST', 'ending_process', 
                                {'bib_id': bib_id,
                                'holding_id': holding_id,
                                'item_id': item_id,
                                'library_code' : library_code,
                                'department' : department},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)

    def get_api_remaining (self,accept='json'):
        """Retourne le nombre d'appel d'API encore autorisé

        Args:
            accept (str, optional): [description]. Defaults to 'json'.
        """
        status, response = self.request('GET', 'test', { 'ids':None }, accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, response.headers['X-Exl-Api-Remaining']

