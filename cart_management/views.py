from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Count
from django.contrib import messages
from django.core.mail import send_mail

from .services import services_request, services_rdv
from .models import PickupLocation, Items, Appointment

from datetime import datetime, time
from urllib.parse import urlencode
import json
import pytz
import logging
# import os

#Initialisation des logs
logger = logging.getLogger(__name__)

def index(request,user_id,institution_id):
    request.session['institution_id'] = institution_id
    request.session['user_id'] = user_id
    return redirect('homepage')

def cart_homepage(request):
    user_id = request.session.get('user_id')
    institution_id = request.session.get('institution_id')
    logger.error("Je viens de la vue")
    error, user = services_request.get_user_info(user_id,institution_id)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return render(request, "cart_management/error.html", locals())
    error, user_carts = services_request.get_user_carts(user,institution_id)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support.')
        return render(request, "cart_management/error.html", locals())
    if not user_carts :
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
    item_from_other_library = cart_list[pickup_loc_id]["item_from_other_library"]
    pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
    # Liste des réservations
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
    #Je lance la suppression de la deamnde
    reponse = services_request.delete_user_request(user_id, request_id, institution)
    if reponse == "Success" :
        #Je vais supprimer la demande en base
        deleted_request = Items.objects.get(user_request_id = request_id)
        deleted_request.delete()
        request_list = request.session.get('cart_list')
        #Il est possible qu'à l'issue de la suppression de la réservation la panier soit vide. On renvoi alors vers la page d'accueil qui rafraichira toutes données de réservation
        user_requests_nb = user_requests_list =  Items.objects.filter(pickuplocation=pickup_loc_id).filter(person=user_id).filter(booked=False).order_by('library_name', 'location').count()
        if user_requests_nb == 0:
            messages.success(request, "Le document a été retiré de votre panier. Vous n'avez plus de résearvation en cour pour la bibliothèque {}".format(pickup_loc.name))
            return redirect('homepage')
        messages.success(request, "Le document a été retiré de votre panier.")
    else:
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
    return redirect('cart-validation', pickup_loc_id=pickup_loc_id)

def rdv(request, pickup_loc_id, user_id, date_rdv):
    date_rdv_in_date = datetime.strptime(date_rdv, '%Y-%m-%d %H:%M:%S')
    # date_rdv_in_date = date_rdv
    pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
    error, user = services_request.get_user_info(user_id,pickup_loc.institution)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
        return redirect('cart-validation', pickup_loc_id=pickup_loc_id)
    ##On raffraichi et récupère la liste des résa du lecteur pour la bib
    error,title_list = services_request.refresh_user_request(user,pickup_loc)
    if error :
        messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
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
    services_request.update_user_request(appointment,title_list,pickup_loc.institution)
    # for title in title_list 
    #2 - On envoi un mail à l'opérateur de commande 
    html_message = loader.render_to_string("cart_management/admin_mail_message.html", locals())
    send_mail(
        "{} : Nouvelle commande pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
        "Ce message contient en pièce jointe les informations de réservation d'un lecteur",
        pickup_loc.email,
        [pickup_loc.email],
        fail_silently=False,
        html_message=html_message,
    )
    #3 - On envoi un mail à l'usager
    plain_message = loader.render_to_string("cart_management/user_mail_message.txt", locals())
    send_mail(
        "{} : Votre demande de Clic et collecte est validée pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
        plain_message,
        pickup_loc.email,
        [user.email],
        fail_silently=False,
    )
    #5 - On regarde s'il reste des paniers à valider
    institution_id = request.session.get('institution_id')
    other_cart_list = Items.objects.filter(person=user.id_alma).filter(appointment__isnull=True).values('pickuplocation','pickuplocation__name').annotate(total=Count('user_request_id')).order_by('total')
    return render(request, "cart_management/confirmation_page.html", locals())