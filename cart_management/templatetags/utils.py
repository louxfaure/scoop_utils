from django import template
from django.contrib import admin
from django.urls import reverse
from datetime import datetime
import json
from ..models import PickupLocation

register = template.Library()

class CustomRequest:
    def __init__(self, user):
        self.user = user

@register.simple_tag(takes_context=True)

def get_app_list(context, **kwargs):
    print(context)
    custom_request = CustomRequest(context['request'].user)
    app_list = admin.site.get_app_list(custom_request)
    return app_list

@register.simple_tag

def get_library_list():
    library_list = PickupLocation.objects.all()
    return library_list

@register.simple_tag

def get_library_url(library_id):
    url = reverse('admin:cart_management_appointment_changelist', 
              current_app='cart_management_appointment')
    now= datetime.today()
    library_url = "{}?library__id_alma__exact={}&date__gte={}".format(url,library_id,now.strftime("%Y-%m-%d"))
    return library_url

@register.simple_tag

def get_url_booking_not_done(library_id):
    url = reverse('admin:cart_management_appointment_changelist', 
              current_app='cart_management_appointment')
    now= datetime.today()
    library_url = "{}?library__id_alma__exact={}&date__lt={}".format(url,library_id,now.strftime("%Y-%m-%d"))
    return library_url