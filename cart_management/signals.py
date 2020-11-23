from django.db.models.signals import pre_delete, post_save
from django.dispatch.dispatcher import receiver
from .models import Items
from .services import services_request

@receiver(post_save, sender=Items)
def _items_save(sender, instance, **kwargs):
    print("SIGNAL SAVE")
    print(instance.user_request_id)
    print(instance.person.id_alma)
    print(instance.pickuplocation.institution)


@receiver(pre_delete, sender=Items)
def _items_delete(sender, instance, **kwargs):
    
    
    print("SIGNAL DELETE")
    print(instance.user_request_id)
    #On Supprime la résa dans Alma
    reponse = services_request.delete_user_request(instance.person.id_alma, instance.user_request_id, instance.pickuplocation.institution)
    print(reponse)
    if reponse != "Success" :
        raise Exception("La suppression dans Alma a planté")
    #     #Je vais supprimer la demande en base
    #     deleted_request = Items.objects.get(user_request_id = request_id)
    #     deleted_request.delete()
    #     request_list = request.session.get('cart_list')
    #     #Il est possible qu'à l'issue de la suppression de la réservation la panier soit vide. On renvoi alors vers la page d'accueil qui rafraichira toutes données de réservation
    #     user_requests_nb = Items.objects.filter(pickuplocation=pickup_loc_id).filter(person=user_id).filter(appointment__isnull=True).order_by('library_name', 'location').count()
    #     if user_requests_nb == 0:
    #         messages.success(request, "Le document a été retiré de votre panier. Vous n'avez plus de résearvation en cours pour la bibliothèque {}".format(pickup_loc.name))
    #         return redirect('homepage')
    #     messages.success(request, "Le document a été retiré de votre panier.")
    # else:
    #     messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')

      
