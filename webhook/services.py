import os
import logging
import json

import base64
import hashlib
import hmac

from cart_management.services.Alma_services import Alma_Apis_Users, Alma_Apis_Records
from cart_management.models import Person,PickupLocation, Items
from django.conf import settings
from cart_management.services import services_request, services_rdv

#Initialisation des logs
logger = logging.getLogger(__name__)

def test_hmac(request):
    """Test le code d'authentification hmac fourni par le WEbHOOK
    Args:
        request (object): requete

    Returns:
        boolean: [description]
    """
    secret_key = settings.WEBHOOK_SECRET_KEY
    signature = request.META.get('HTTP_X_EXL_SIGNATURE')
    if not signature:
        logger.error("Le webhook n'a pas fourni de signature")
        return False
    body = request.body
    key = secret_key.encode('utf-8')
    received_hmac_b64 = signature.encode('utf-8')
    generated_hmac = hmac.new(key=key, msg=body, digestmod=hashlib.sha256).digest()
    generated_hmac_b64 = base64.b64encode(generated_hmac)
    match = hmac.compare_digest(received_hmac_b64, generated_hmac_b64)
    if not match: 
        logger.error("Le HMAC n'est pas valide !")
    else :
        return True

def event_dispatcher(event,api_key,request_data):
    """Déclencle les actions adéquates en fonction de l'évènement

    Args:
        event (string): Type d'évenement REQUEST_PLACED_ON_SHELF, REQUEST_CREATED, REQUEST_CANCELED, REQUEST_CLOSED
        request_data (dict): Corps de la reservation json converti en dict
    """
    # TO DO FILTRER SUR LA PICKUPLOC + Place in QUEUE
    try:
        pickup_loc = PickupLocation.objects.get(id_alma=request_data["user_request"]["pickup_location_library"])
    except PickupLocation.DoesNotExist:
            return "Le clique et colete n'est pas géré pour cette bibliothèque", 418
    if event == "REQUEST_CREATED" :
        alma_inst = request_data["institution"]["value"]
        inst = alma_inst.replace("33PUDB_","")
        user_id = request_data["user_request"]["user_primary_id"]
        error, user = services_request.get_user_info(user_id,inst)
        if error :
            return "Utilisateur inconnu", 418
        services_request.get_user_request_item(request_data["user_request"],api_key,user)
        return "Reservation créée avec succés", 200
    if event == "REQUEST_CANCELED" :
        try:
            user_request_item = Items.objects.get(user_request_id=request_data["user_request"]["request_id"])
        except Items.DoesNotExist:
            return "La réservation n'existe pas. J'ai rien fait", 200    
        user_request_item.delete()
        return "Reservation supprimée avec succés", 200
    if event == "REQUEST_PLACED_ON_SHELF" :
        try:
            user_request_item = Items.objects.get(user_request_id=request_data["user_request"]["request_id"])
        except Items.DoesNotExist:
            return "La réservation n'existe pas. Impossible de modifier le tatut", 500    
        user_request_item.status = request_data["user_request"]["request_status"]
        user_request_item.save()
        return "Statut de la reservation supprimée avec succés", 200
    if event == "REQUEST_CLOSED" :
        try:
            user_request_item = Items.objects.get(user_request_id=request_data["user_request"]["request_id"])
        except Items.DoesNotExist:
            return "La réservation n'existe pas. Impossible de modifier le tatut", 500    
        user_request_item.status = "ON_LOAN"
        user_request_item.save()
        return "Statut de la reservation supprimée avec succés", 200
    return "Type d'évenement non géré par l'application C&C", 418
        