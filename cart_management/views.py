from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Count
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives

from .services import services_request, services_rdv
from .models import PickupLocation, Items, Appointment

from datetime import datetime, time
from urllib.parse import urlencode
import json
import pytz
import logging
import threading
# import os

#Initialisation des logs
logger = logging.getLogger(__name__)

#Thread pour l'ajout de la date et l'heure de rdv dans Alma
class UpdateUserRequestThread(threading.Thread):

    def __init__(self,appointment,title_list,institution):
        self.appointment = appointment
        self.title_list = title_list
        self.institution = institution
        threading.Thread.__init__(self)

    def run(self):
        logger.info("starting UpdateUserRequestThread")
        try : 
            services_request.update_user_request(self.appointment,self.title_list,self.institution)
        except Exception as e:
            logger.error("ERROR UpdateUserRequestThread :: {}".format(e))

        logger.info("Ending UpdateUserRequestThread")


#Tread pour l'envoi du mail récapitulatif à l'usager
class EmailThread(threading.Thread):

    def __init__(self,email,mail_type):
        self.email = email
        self.mail_type = mail_type
        threading.Thread.__init__(self)

    def run(self):
        logger.info("starting EmailThread : {}".format(self.mail_type))
        try :
            self.email.send(fail_silently=False)
        except Exception as e:
            logger.error("ERROR EmailThread {} :: {}".format(self.mail_type,e))
        logger.info("Ending EmailThread : {}".format(self.mail_type))

def index(request,user_id,institution_id):
    request.session['institution_id'] = institution_id[7:]
    request.session['user_id'] = user_id
    return redirect('homepage')

def cart_homepage(request):
    """Page d'accueil du service regarde si l'usager existe et a des réservations.
    Si oui, groupe les résa par institution et par bibliothèque
    Renvoie vers la page de validation du panier et de choix d'une plage de rdv
    """
    user_id = request.session.get('user_id')
    institution_id = request.session.get('institution_id')
    if user_id in [None, ''] or institution_id in [None, ''] :
        return render(request, "cart_management/panier_vide.html", locals())
    # On récupère les infos du lecteur
    error, user = services_request.get_user_info(user_id,institution_id)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return render(request, "cart_management/error.html", locals())
    # On récupère les résas de l'usager
    error, user_carts = services_request.get_user_carts(user)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return render(request, "cart_management/error.html", locals())
    if not user_carts :
        del request.session['user_id']
        if ('cart_list' in request.session) :
            del request.session['cart_list']
        return render(request, "cart_management/panier_vide.html", locals())
    user.save()
    request.session['cart_list'] = user_carts
    if len(user_carts) == 1 :
        pickup_loc = list(user_carts.keys())[0] 
        return redirect('cart-validation', pickup_loc_id=pickup_loc)    
    return render(request, "cart_management/homepage.html", locals())

def cart_validation(request, pickup_loc_id):
    user_id = request.session.get('user_id')
    cart_list = request.session.get('cart_list')
    institution_id = request.session.get('institution_id')
    if user_id in [None, ''] or institution_id in [None, ''] or cart_list in [None, ''] :
        return render(request, "cart_management/panier_vide.html", locals())
    
    # Liste des réservations
    # Au cas où un panier reste présent dans les variables de session et que l'id de la pickup location ne correspond pas 
    try : 
        item_from_other_library = cart_list[pickup_loc_id]["item_from_other_library"]        
    except Exception as e:
        return redirect('index', user_id=user_id, institution_id=institution_id)
    pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
    user_requests_list =  Items.objects.filter(pickuplocation=pickup_loc_id).filter(person=user_id).filter(appointment__isnull=True).order_by('library_name', 'location')
    # Proposition des RDV
    if item_from_other_library :
        handling_time = pickup_loc.handling_time_external_library
    else:
        handling_time = pickup_loc.handling_time
    resas = services_rdv.Resas(pickup_loc,pickup_loc.open_hour,pickup_loc.close_hour, pickup_loc.plot_number,handling_time,pickup_loc.days_for_booking)
    list_hours = resas.get_list_hours_for_public_view()
    return render(request, "cart_management/cart_validation.html", locals())

def request_delation(request, request_id, institution, pickup_loc_id):
    user_id = request.session.get('user_id')
    pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
    deleted_request = Items.objects.get(user_request_id = request_id)
    try:
        deleted_request.delete()
    except:
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
    #Je lance la suppression de la demande
    reponse = services_request.delete_user_request(user_id, request_id, institution)
    request_list = request.session.get('cart_list')
    #Il est possible qu'à l'issue de la suppression de la réservation la panier soit vide. On renvoi alors vers la page d'accueil qui rafraichira toutes données de réservation
    user_requests_nb = Items.objects.filter(pickuplocation=pickup_loc_id).filter(person=user_id).filter(appointment__isnull=True).order_by('library_name', 'location').count()
    if user_requests_nb == 0:
        messages.success(request, "Le document a été retiré de votre panier. Vous n'avez plus de résearvation en cours pour la bibliothèque {}".format(pickup_loc.name))
        return redirect('homepage')
    messages.success(request, "Le document a été retiré de votre panier.")
    return redirect('cart-validation', pickup_loc_id=pickup_loc_id)

def rdv(request, pickup_loc_id, user_id, date_rdv):
    print("Debut traitement")
    date_rdv_in_date = datetime.strptime(date_rdv, '%Y-%m-%d %H:%M:%S')
    pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
    error, user = services_request.get_user_info(user_id,pickup_loc.institution)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return redirect('cart-validation', pickup_loc_id=pickup_loc_id)
    ##On raffraichi et récupère la liste des résa du lecteur pour la bib
    error,title_list = services_request.refresh_user_request(user,pickup_loc)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return redirect('cart-validation', pickup_loc_id=pickup_loc_id)
    # On créé un rdv pour l'usager
    appointment = Appointment(date=date_rdv, person=user, library=pickup_loc)
    try:
        appointment.save()
    except IntegrityError as e: 
        if 'UNIQUE constraint' in e.args[0]:
            messages.error(request, "Cette plage vient d'être réservée par un autre utilisateur. Merci d'en choisir une nouvelle")
            return redirect('cart-validation', pickup_loc_id=pickup_loc_id)
        else:
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return redirect('cart-validation', pickup_loc_id=pickup_loc_id) 
    except Exception as e:
        logger.error('Erreur : {}'.format(e))
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
        return redirect('cart-validation', pickup_loc_id=pickup_loc_id) 
    #1 - On va marquer dans Alma les résas comme traité en ajoutant une note et une date de fin d'intéret + on attache notre rdv à la résa
    UpdateUserRequestThread(appointment,title_list,pickup_loc.institution).start()
    #2 - On envoi un mail à l'usager
    plain_message = loader.render_to_string("cart_management/user_mail_message.txt", locals())
    user_email = EmailMessage(
        "{} : Votre demande de Clic et collecte est validée pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
        plain_message,
        pickup_loc.from_email,
        [user.email],
    )
    EmailThread(user_email,"user_email").start()
    
    #3 - On envoi un mail à l'opérateur de commande 
    html_message = loader.render_to_string("cart_management/admin_mail_message.html", locals())
    library_email = EmailMultiAlternatives(
        "{} : Nouvelle commande pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
        "Ce message contient en pièce jointe les informations de réservation d'un lecteur",
        pickup_loc.from_email,
        [pickup_loc.email],
        # fail_silently=True,
        # html_message=html_message,
    )
    library_email.attach_alternative(html_message, "text/html")
    html_message.content_subtype = "html"
    EmailThread(library_email,"library_email").start()
    # try : send_mail(
    #     "{} : Nouvelle commande pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
    #     "Ce message contient en pièce jointe les informations de réservation d'un lecteur",
    #     pickup_loc.from_email,
    #     [pickup_loc.email],
    #     fail_silently=True,
    #     html_message=html_message,
    # )
    # except Exception as e:
    #     logger.error('Erreur Mail Biblio : {}'.format(e))
    #         #5 - On regarde s'il reste des paniers à valider
    #     institution_id = request.session.get('institution_id')
    #     other_cart_list = Items.objects.filter(person=user.id_alma).filter(appointment__isnull=True).values('pickuplocation','pickuplocation__name').annotate(total=Count('user_request_id')).order_by('total')
    #     return render(request, "cart_management/confirmation_page.html", locals())
    #5 - On regarde s'il reste des paniers à valider
    institution_id = request.session.get('institution_id')
    other_cart_list = Items.objects.filter(person=user.id_alma).filter(appointment__isnull=True).values('pickuplocation','pickuplocation__name').annotate(total=Count('user_request_id')).order_by('total')
    return render(request, "cart_management/confirmation_page.html", locals())

def mail(request):
    email = EmailMessage(
        'Hello',
        'Body goes here',
        'alexandre.faure@u-bordeaux.fr',
        ['alexandre.faure@u-bordeaux.fr'],
        )
    EmailThread(email,"test").start()
    return render(request, "cart_management/mail.html", locals())