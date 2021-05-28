from django.http import HttpResponse, JsonResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .services import *
from cart_management.services import services_request, services_rdv
import json

#Initialisation des logs
logger = logging.getLogger(__name__)
@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        if test_hmac(request) :
            # resa = request.body
            resa = json.loads(request.body)
            logger.debug(json.dumps(resa, indent=4, sort_keys=True))
            event=resa["event"]["value"]
            type_resa=resa["user_request"]["request_type"]
            ss_type_resa=resa["user_request"]["request_sub_type"]["value"]
            alma_inst = resa["institution"]["value"]
            inst = alma_inst.replace("33PUDB_","")
            api_key = settings.ALMA_API_KEY[inst]
            logger.debug("{} -- {} -- {}".format(event,type_resa,ss_type_resa))
            if type_resa == "HOLD" and ss_type_resa == "PATRON_PHYSICAL" :
                message, status = event_dispatcher(event,api_key,resa)
                return HttpResponse(message, status=status)
            else:
                return HttpResponse("Type de requête non traité", status=418)    

            
        else :
            return HttpResponse("Le HMAC n'apas été validé",status=500)
    else :
        try: 
            challenge = { 'challenge' : request.GET["challenge"] } 
        except MultiValueDictKeyError:
            return HttpResponse("Bien reçu. Pas de Challenge.")
        return JsonResponse(challenge)