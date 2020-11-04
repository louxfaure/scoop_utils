import os
import re
# external imports
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import logging
import xml.etree.ElementTree as ET
import time



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
    'get_user' : 'users/{user_id}?view={user_view}&expand={user_expand}',
    'get_user_with_id_type' : 'users/{user_id}?user_id_type={user_id_type}&view={user_view}&expand={user_expand}',
    'retrieve_user_by_id' : 'users?limit=10&offset=0&q=primary_id~{user_id}',
    'delete_user' : 'users/{user_id}',
    'update_user' : 'users/{user_id}?user_id_type=all_unique&override={param_override}',
    'get_user_loans' : 'users/{user_id}/loans?user_id_type={user_id_type}&limit={limit}&offset={offset}',
    'get_user_requests' : 'users/{user_id}/requests?request_type={request_type}&user_id_type={user_id_type}&limit={limit}&offset={offset}&status={status}',
    'delete_user_requests' : 'users/{user_id}/requests/{request_id}?reason{reason}&notify_user={notify_user}',
    'get_user_request' : 'users/{user_id}/requests/{request_id}',
    'update_user_request' : 'users/{user_id}/requests/{request_id}',

}

NS = {'sru': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'xmlb' : 'http://com/exlibris/urm/general/xmlbeans'
         }

class AlmaUsers(object):
    """A set of function for interact with Alma Apis in area "User & Fullfilment"
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
        #print(content_type)
        headers = {
            "User-Agent": "pyalma/{}".format(__version__),
            "Authorization": "apikey {}".format(self.apikey),
            "Accept": FORMATS[accept]
        }
        if content_type is not None:
            headers['Content-Type'] = FORMATS[content_type]
        #print(headers)
        return headers
    def get_error_message(self, response, accept):
        """Extract error code & error message of an API response
        
        Arguments:
            response {object} -- API REsponse
        
        Returns:
            int -- error code
            str -- error message
        """
        data = re.sub(r'\s+', '', response.text)
        if (re.match(r'^<.+>$', data)):
            root = ET.fromstring(response.text)
            error_message = root.find(".//xmlb:errorMessage",NS).text if root.find(".//xmlb:errorMessage",NS).text else response.text 
            error_code = root.find(".//xmlb:errorCode",NS).text if root.find(".//xmlb:errorCode",NS).text else '???'
            return error_code, error_message
        elif (re.match(r'^{|[).+(}|]$', data)):
            content = response.json()
            if ('web_service_result' in content):
                error_message = content['web_service_result']['errorList']['error']['errorMessage']
                error_code = content['web_service_result']['errorList']['error']['errorCode']
                return error_code, error_message
            else :
                error_message = content['errorList']['error'][0]['errorMessage']
                error_code = content['errorList']['error'][0]['errorCode']
                return error_code, error_message
        else:
            return 666, 'Format de réponse invalide'
    
    def request(self, httpmethod, resource, ids, params={}, data=None,
                accept='json', content_type=None, nb_tries=0):
        #print(content_type)
        #20190905 retry request 3 time s in case of requests.exceptions.ConnectionError
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        response = session.request(
            method=httpmethod,
            headers=self.headers(accept=accept, content_type=content_type),
            url=self.fullurl(resource, ids),
            params=params,
            data=data)
        #print(response.url)
        try:
            response.raise_for_status()  
        except requests.exceptions.HTTPError:
            #print(response.text)
            error_code, error_message= self.get_error_message(response,accept)
            self.logger.error("Alma_Apis :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(response.status_code,response.request.method, response.url, response.text))
            if error_code in ['401890','401861'] :
                return 'No record found', "{} -- {}".format(error_code, error_message)
            else : 
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
    
    def retrieve_user_by_id(self, user_id,accept='xml'):
        """Utilise l'Api Retrieve pour savoir si l'usager est présent dans une institution
        
        Arguments:
            user_id {str} -- identifiant du lecteur
        
        Returns:
            status {str} -- Success or Error
            response {str} -- Message d'erreurs ou Liste de résultats 
        """
        status,response = self.request('GET', 'retrieve_user_by_id',
                                {'user_id' : user_id},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, self.extract_content(response)



    def get_user(self, user_id, user_id_type='PRIMARYIDENTIFIER' , user_expand='loans,requests', user_view='brief',accept='xml'):
        """Retourne un usager à partir d'un identifiant
        
        Arguments:
            user_id {str} -- identifiant du lecteur
        
        Keyword Arguments:
            user_id_type {str} -- type d'identifiant sure lequel effectué la recherche BARCODE ou PRIMARYIDENTIFIER (default: {'PRIMARYIDENTIFIER'})
            user_expand {str} -- informations supllémentaires: (default: {'loans'})
            user_view {str} -- affichage complet full ou brief  (default: {'brief'})
            accept {str} -- format de sortie xml ou json (default: {'xml'})
        
        Returns:
            status {str} -- Success or Error
            response {str} -- Message d'erreurs ou Lecteur 
        """
        url = 'get_user'
        if  user_id_type != 'PRIMARYIDENTIFIER' :
            url = 'get_user_with_id_type'
        status,response = self.request('GET', url,
                                {'user_id' : user_id,
                                'user_id_type' : user_id_type,
                                'user_view' : user_view,
                                'user_expand' : user_expand},
                                accept=accept)
        if status == 'Success':
            return status, self.extract_content(response)
        else:
            return status, response

    def delete_user(self, user_id, accept='xml'):
        """Supprime un usager à partir de son identifiant
        
        Arguments:
            user_id {str} -- identifiant du lecteur
        
        
        Returns:
            [type] -- [description]
        """
        status,response = self.request('DELETE', 'delete_user',
                                {'user_id' : user_id},
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status, response.status_code

    def update_user(self, user_id, override, data ,accept='xml',content_type='xml'):
        """Mets à jour lesinformations utilistaeurs
        
        Arguments:
            user_id {str} -- identifiant de l'utilisateur Primary Id ou Barcode
            force_update {str} -- Par défaut certains champs sont protégés. Pour forcer leurs mis àjour il faut renseigner le paramètre override.
            Valeurs par défaut :user_group, job_category, pin_number, preferred_language, campus_code, rs_libraries, user_title, library_notices
            data {json ou xml} -- object lecteur en json ou xml selon le parmètre passer à accept
        
        Keyword Arguments:
            accept {str} -- xml ou json (default: {'xml'})
        
        Returns:
            status {str} -- Success or Error
            response {str} -- Message d'erreurs ou Lecteur MOdifié
        """ 

        status,response = self.request('PUT', 'update_user',
                                {'user_id' : user_id,
                                'param_override' : override },
                                data=data,
                                accept=accept,
                                content_type=content_type)
        if status == 'Error':
            return status, response
        else:
            return status,  self.extract_content(response)

    def get_user_loans(self,user_id, user_id_type = 'all_unique',limit = 50, offset = 0, accept ='xml'):
        """ Get user loans

        Arguments:
            user_id {str} -- A unique identifier for the user

        Keyword Arguments:
            user_id_type {str} -- The type of identifier that is being searched. Optional. If this is not provided, all unique identifier types are used. The values that can be used are any of the values in UserIdentifierTypes code table. (default: {'allunique'})
            limit {int} -- mits the number of results. Optional. Valid values are 0-100. (default: {20})
            offset {int} -- Offset of the results returned. (default: {0})
            accept {str} -- [description] (default: {'xml'})
        """
        status,response = self.request('GET', 'get_user_loans',
                                {'user_id' : user_id,
                                'user_id_type' : user_id_type,
                                'limit' : limit,
                                'offset' : offset},
                                accept=accept)
        if status == 'Success':
            return status, self.extract_content(response)
        else:
            return status, response
    
    def get_user_requests(self,user_id,request_type, user_id_type = 'all_unique',limit = 50, offset = 0, status = 'active', accept ='xml'):
        """ Get user requests

        Arguments:
            user_id {str} -- A unique identifier for the user
            request_type {str} -- Filter results by request type.Possible values: HOLD, DIGITIZATION, BOOKING.

        Keyword Arguments:
            user_id_type {str} -- The type of identifier that is being searched. Optional. If this is not provided, all unique identifier types are used. The values that can be used are any of the values in UserIdentifierTypes code table. (default: {'allunique'})
            limit {int} -- mits the number of results. Optional. Valid values are 0-100. (default: {20})
            offset {int} -- Offset of the results returned. (default: {0})
            status {str} -- Active or History request status. Default is active. The 'history' option is only available if the 'should_anonymize_requests' customer parameter is set to 'false' at the time the request was completed. (default: {'active'})
            accept {str} -- [description] (default: {'xml'})
        """
        status,response = self.request('GET', 'get_user_requests',
                                {'user_id' : user_id,
                                'request_type' : request_type,
                                'user_id_type' : user_id_type,
                                'limit' : limit,
                                'offset' : offset,
                                'status' : status},
                                accept=accept)
        if status == 'Success':
            return status, self.extract_content(response)
        else:
            return status, response

    def delete_user_request(self,user_id,request_id, reason = 'CancelledAtPatronRequest',notify_user = 'false', accept ='xml'):
        """Delete a user request

        Arguments:
            user_id {[str]} -- A unique identifier for the user
            request_id {str} -- A unique identifier of the request that should be canceled.

        Keyword Arguments:
            reason {str} -- Code of the cancel reason. Must be a value from the code table 'RequestCancellationReasons' (default: {'CancelledAtPatronRequest'})
            notify_user {str} -- Boolean flag for notifying the requester of the cancellation (when relevant). (default: {'false'})
            accept {str} -- [description] (default: {'xml'})
        """
        status,response = self.request('DELETE', 'delete_user_requests',
                                {'user_id' : user_id,
                                'request_id' : request_id,
                                'reason' : reason,
                                'notify_user' : notify_user},
                                accept=accept)
        if status == 'Success':
            return status, response
        else:
            return status, response
    
    def get_user_request(self, user_id, request_id,accept='xml'):
        """Mets à jour les informations pour une deamnde 
        
        Arguments:
            user_id {str} -- identifiant de l'utilisateur Primary Id ou Barcode
            request_id {str} -- identifiant de la deamnde
        
        Keyword Arguments:
            accept {str} -- xml ou json (default: {'xml'})
        
        Returns:
            status {str} -- Success or Error
            response {str} -- Message d'erreurs ou requete MOdifié
        """ 

        status,response = self.request('GET', 'get_user_request',
                                {'user_id' : user_id,
                                'request_id' : request_id },
                                accept=accept)
        if status == 'Error':
            return status, response
        else:
            return status,  self.extract_content(response)

    def update_user_request(self, user_id, reques_id, data ,accept='xml',content_type='xml'):
        """Mets à jour les informations pour une deamnde 
        
        Arguments:
            user_id {str} -- identifiant de l'utilisateur Primary Id ou Barcode
            reques_id {str} -- identifiant de la deamnde
            data {json ou xml} -- object lecteur en json ou xml selon le parmètre passer à accept
        
        Keyword Arguments:
            accept {str} -- xml ou json (default: {'xml'})
        
        Returns:
            status {str} -- Success or Error
            response {str} -- Message d'erreurs ou requete MOdifié
        """ 

        status,response = self.request('PUT', 'update_user_request',
                                {'user_id' : user_id,
                                'request_id' : reques_id },
                                data=data,
                                accept=accept,
                                content_type=content_type)
        if status == 'Error':
            return status, response
        else:
            return status,  self.extract_content(response)