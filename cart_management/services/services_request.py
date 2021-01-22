import os
import logging
import json

from .Alma_services import Alma_Apis_Users, Alma_Apis_Records
from ..models import Person,PickupLocation, Items
from django.conf import settings

#Initialisation des logs
logger = logging.getLogger(__name__)

def get_alma_barcode(identifiers_list):
    """Prend une liste d'identifiant et retourne un code-barre
    """
    for identifier in identifiers_list:
        if identifier['id_type']['value'] == 'BARCODE':
            return identifier['value']
    return "None"

def get_user_info(user_id,institution):
    """Return an user object

    Arguments:
        user_id {str} -- Alma Primary id of user
        institution {str} -- Institution code from Primo
    """
    try:
        person = Person.objects.get(id_alma=user_id)
        return False, person
    except Person.DoesNotExist:
        api_key = settings.ALMA_API_KEY[institution] 
        api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='get_user_info')
        status, user = api.get_user(user_id,accept='json')
        if status == "Success":
            u = Person( id_alma = user_id,
                        barcode = get_alma_barcode(user['user_identifier']),
                        first_name = user['first_name'],
                        last_name = user['last_name'],
                        email = user['contact_info']['email'][0]['email_address']
                        )
            # return False, u           
            u.save()
            return False, u
        else :
            return True,user

def get_holding_info(holdings_list,library):
    """Return some info of the holding in a holdings list for a libarry pass in parameter

    Arguments:
        holdings_list {[type]} -- [description]
        library {[type]} -- [description]

    Returns:
        [dict] -- [description]
    """
    holding_info = {}
    for holding in holdings_list:
        if holding['library']['desc'] == library :
                holding_info['call_number'] = holding['call_number'] if 'call_number' in holding.keys() else "None"
                holding_info['location'] = holding['location']['desc']
                holding_info['library_id'] = holding['library']['value']
                holding_info['library_name'] = holding['library']['desc']
                return holding_info
    if library in ['Bib. pluridisciplinaire','Spot Pessac','BU Sciences et techniques'] :
        for holding in holdings_list:
            if holding['library']['desc'] == "BU droit, science politique, économie" :
                    holding_info['call_number'] = holding['call_number'] if 'call_number' in holding.keys() else "None"
                    holding_info['location'] = holding['location']['desc']
                    holding_info['library_id'] = holding['library']['value']
                    holding_info['library_name'] = holding['library']['desc']
                    return holding_info
    holding_info['call_number'] = "None"
    holding_info['location'] = "None"
    holding_info['library_id'] = "None"
    holding_info['library_name'] = "None"
    return holding_info

        
    

def get_user_request_item(user_request,api_key,user):
    """Get title info for user request create an item object and return it

    Arguments:
        user_request {dict} -- a user request
        api_key {str} -- [description]
    """
    record_api = Alma_Apis_Records.AlmaRecords(api_key, region='EU', service='pickup_collect')
    # logger.info(user_request)
    try:
        user_request_item = Items.objects.get(user_request_id=user_request['request_id'])
    except Items.DoesNotExist:
        user_request_item = Items(  user_request_id = user_request['request_id'],
                                    library_name = user_request['managed_by_library'],
                                    library_id = None,
                                    location = None,
                                    call_number = None,
                                    title = user_request['title'][0:450],
                                    item_barcode = user_request['barcode'],
                                    description = user_request['description'] if 'description' in user_request else None,
                                    manual_description = user_request['manual_description'] if 'manual_description' in user_request else None,
                                    pickuplocation = PickupLocation.objects.get(id_alma=user_request['pickup_location_library']),
                                    person = user,
                                    status = user_request['request_status']
                            )
        if user_request['barcode'] is not None:
            status,item = record_api.get_item_with_barcode(user_request['barcode'],accept='json')
            if status == "Success":
                if item['holding_data']['in_temp_location'] == "true" :
                    user_request_item.call_number = item['holding_data']['call_number']
                    user_request_item.location = item['holding_data']['temp_location']['desc']
                    user_request_item.library_id = item['holding_data']['temp_library']['value']
                    user_request_item.library_name = item['holding_data']['temp_library']['desc']
                else :
                    user_request_item.call_number = item['holding_data']['call_number']
                    user_request_item.location = item['item_data']['location']['desc']
                    user_request_item.library_id = item['item_data']['library']['value']
                    user_request_item.library_name = item['item_data']['library']['desc']
        # Cas d'une reservation qui a été placée sur l'exemplaire on va se baser sur les informatiosn de la holding
        else:
            #1- On va chercher la liste des holdinggs sous la notice biblio
            status,reponse=record_api.get_holdings_list(user_request['mms_id'],accept='json')
            if status == "Success":
                holding = get_holding_info(reponse['holding'],user_request['managed_by_library'])
                user_request_item.call_number = holding['call_number']
                user_request_item.location = holding['location']
                user_request_item.library_id = holding['library_id']
                user_request_item.library_name = holding['library_name']
        user_request_item.save()
    return user_request_item



def get_user_carts(user):
    """Return a list of carts. Cart are requests user placed on the same pickup library. 

    Arguments:
        user_id {obj} -- user object
        institution {str} -- Institution code from Primo
    """
    
    #Search for user requests
    user_carts_list = {}
    for institution in settings.INSTITUTIONS_LIST :
        # api_key = os.getenv("PROD_{}_USER_API".format(institution))
        api_key = settings.ALMA_API_KEY[institution]
        api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
        status, user_requests = api.get_user_requests(user.id_alma,'HOLD',limit = 50,accept='json')
        # logger.info("{} --> {} : {}".format(institution,status,user_requests))
        if status == "Success":
            # print("{} --> {} : {}".format(institution,status,requests['total_record_count']))
            if  user_requests['total_record_count'] > 0:
                for user_request in user_requests["user_request"]:                   
                    if "last_interest_date" not in user_request:
                        pickup_location_library = user_request['pickup_location_library']
                        try:
                            pickuplocation = PickupLocation.objects.get(id_alma=user_request['pickup_location_library'])
                            if pickup_location_library not in  user_carts_list:
                                user_carts_list[pickup_location_library] = {}
                                user_carts_list[pickup_location_library]["user_request_list"] = []
                                user_carts_list[pickup_location_library]["item_from_other_library"] = False
                                user_carts_list[pickup_location_library]["name"] = user_request['pickup_location']
                            user_request_item = get_user_request_item(user_request,api_key,user)
                            if user_request['managed_by_library_code'] != pickup_location_library :
                                user_carts_list[pickup_location_library]["item_from_other_library"] = True                 
                            user_carts_list[pickup_location_library]["user_request_list"].append(user_request_item.user_request_id)
                        except PickupLocation.DoesNotExist:
                            pickuplocation = 'none'
        elif status == "Error":
            return True,user_requests
    return False,user_carts_list       

def get_user_carts_admin(user,institution,library):
    """Return a list of carts. Cart are requests user placed on the same pickup library. 

    Arguments:
        user_id {obj} -- user object
        institution {str} -- Institution code from Primo
    """
    
    #Search for user requests
    user_carts_list = {}
    # api_key = os.getenv("PROD_{}_USER_API".format(institution))
    api_key = settings.ALMA_API_KEY[institution]
    api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
    status, user_requests = api.get_user_requests(user.id_alma,'HOLD',limit = 50,accept='json')
    # logger.info("{} --> {} : {}".format(institution,status,user_requests))
    if status == "Success":
        # print("{} --> {} : {}".format(institution,status,requests['total_record_count']))
        if  user_requests['total_record_count'] > 0:
            for user_request in user_requests["user_request"]:                   
                if user_request['pickup_location_library'] == library and "last_interest_date" not in user_request:
                    pickup_location_library = user_request['pickup_location_library']
                    if library not in  user_carts_list:
                        user_carts_list[library] = {}
                        user_carts_list[library]["user_request_list"] = []
                        user_carts_list[library]["item_from_other_library"] = False
                        user_carts_list[library]["name"] = user_request['pickup_location']
                    user_request_item = get_user_request_item(user_request,api_key,user)
                    if user_request_item.library_id != library :
                        user_carts_list[library]["item_from_other_library"] = True                 
                    user_carts_list[library]["user_request_list"].append(user_request_item)
    elif status == "Error":
        return True,user_requests
    return False,user_carts_list       


def delete_user_request(user_id,user_request_id,institution):
    api_key = settings.ALMA_API_KEY[institution]
    api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
    statut, reponse = api.delete_user_request(user_id,user_request_id,accept='json')
    if reponse == "401694 -- Request not found" :
        statut = "Success"
    return statut

def refresh_user_request(user,pickup_location):
    """Refresh the list of request items

    Arguments:
        user_id {[type]} -- [description]
        pickup_location {[type]} -- [description]
    """
    # On récupère la liste des réservations en bases
    cart_user_requests_list = list(Items.objects.filter(pickuplocation=pickup_location.id_alma).filter(person=user.id_alma).filter(appointment__isnull=True).values_list('user_request_id', flat=True))
    # On récupère la liste des réservations dans Alma pour l'institution
    api_key = settings.ALMA_API_KEY[pickup_location.institution]
    api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
    status, alma_user_requests_list = api.get_user_requests(user.id_alma,'HOLD',limit = 50,accept='json')
    if status == "Success":
        # print("{} --> {} : {}".format(institution,status,requests['total_record_count']))
        for alma_user_request in alma_user_requests_list["user_request"]:
            if "last_interest_date" not in alma_user_request and alma_user_request['pickup_location_library'] == pickup_location.id_alma :
                if alma_user_request["request_id"] in cart_user_requests_list :
                    cart_user_requests_list.remove(alma_user_request["request_id"])
                else:
                    user_request_item = get_user_request_item(alma_user_request,api_key,user)
        for cart_user_request in cart_user_requests_list:
            user_request_to_delete=Items.objects.get(user_request_id = cart_user_request )
            user_request_to_delete.delete()
    else:
        return True,user_requests
    cart_user_requests_list =  Items.objects.filter(pickuplocation=pickup_location.id_alma).filter(person=user.id_alma).filter(appointment__isnull=True).order_by('library_name', 'location')
    return False,cart_user_requests_list

def update_user_request(appointment,user_requests_list,institution):
    """Indique à Alma qu'on a traité la réservation en mettant à jour la date de fin d'intéret et en joutant un commentaire + Lie la resa au rdv

    Arguments:
        appointment {obj} -- date et heure du retrait du document
        user_requests_list {obj_list} -- toutes les réservations du panier
        institution {str} -- code de l'institution

    Returns:
        [str] -- statut du traitement
    """
    # print(user_requests_list)
    api_key = settings.ALMA_API_KEY[institution]
    api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
    for cart_user_request in user_requests_list:
        id_lecteur = cart_user_request.person
        # print("id lecteur : {}".format(id_lecteur))
        id_resa = cart_user_request.user_request_id
        statut, alma_user_request = api.get_user_request(id_lecteur,id_resa,accept='json')
        # print("{} -- {}".format(statut,json.dumps(alma_user_request, indent=2)))    
        # alma_user_request["last_interest_date"] = appointment.get_date_formatee('alma')
        # alma_user_request["comment"] = "Retrait du document prévu le {}".format(appointment.get_date_formatee('complet'))
        # statut, reponse = api.update_user_request(id_lecteur,id_resa,json.dumps(alma_user_request),accept='json',content_type='json')
        cart_user_request.appointment = appointment
        cart_user_request.save()
    return "Success" 

def get_request_user_status(user_id,user_request_id,institution):
    """TO DO

    Args:
        user_request_id ([type]): [description]

    Returns:
        [type]: [description]
    """
    message_status = {
        "In Process" : "A récupérer en rayon",
        "On Hold Shelf" : "Sur les étagères de réservation",
        "Not Started" : "A récupérer en rayon"
    }
    api_key = settings.ALMA_API_KEY[institution]
    api = Alma_Apis_Users.AlmaUsers(apikey=api_key, region='EU', service='test')
    api_request_return_status, alma_user_request = api.get_user_request(user_id,user_request_id,accept='json')
    if api_request_return_status == "Error":
        return "Statut inconnu"
    if alma_user_request["request_status"] == "HISTORY":
        api_loan_return_status, api_loan_reponse = api.get_user_loans(user_id,limit = 50,accept='json')
        if api_loan_return_status == "Error":
            return "Statut inconnu"
        if api_loan_reponse['total_record_count'] > 0:
            user_loans_list = api_loan_reponse['item_loan']
            for user_loan in user_loans_list:
                if alma_user_request["mms_id"] == user_loan["mms_id"]:
                    return "En prêt sur le compte du lecteur"
            return "Demande annulée"
        else :
            return "Demande annulée"
    return alma_user_request["request_status"]      


