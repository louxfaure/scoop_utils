from django.db.models.signals import pre_delete, post_save
from django.dispatch.dispatcher import receiver
from .models import Items
from .services import services_request

# @receiver(post_save, sender=Items)
# def _items_save(sender, instance, **kwargs):
#     print("SIGNAL SAVE")
#     print(instance.user_request_id)
#     print(instance.person.id_alma)
#     print(instance.pickuplocation.institution)


@receiver(pre_delete, sender=Items)
def _items_delete(sender, instance, **kwargs):
    """ Avant la suppression de la réservation en base suprrime cette dernière dans Alma """
    
    print("SIGNAL DELETE")
    print(instance.user_request_id)
    #On Supprime la résa dans Alma
    reponse = services_request.delete_user_request(instance.person.id_alma, instance.user_request_id, instance.pickuplocation.institution)
    print(reponse)
    if reponse != "Success" :
        raise Exception("La suppression dans Alma a planté")    
