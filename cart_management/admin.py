from django.http import HttpResponse,HttpResponseRedirect
from django.conf.urls import url
from django.urls import path
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import PickupLocation,Person,Items, Appointment,Staff,DaysOfWeek, ClosedDays
from django.template import loader
from django.template.response import TemplateResponse
from .services import services_request, services_rdv
from .forms import AddRdvForm
from datetime import datetime, time
from django.core.mail import send_mail

# from security.models import Security

admin.site.site_title = "Gestion du Clic et Collecte "
admin.site.site_header = "Gestion du Clic et Collecte"
admin.site.index_title = "Gestion du Clic et Collecte"

admin.site.register(DaysOfWeek)
admin.site.register(ClosedDays)


class AppointmentInline(admin.TabularInline):
    model = Appointment
    fields = ['library','date']
    show_change_link = True
    # readonly_fields = ('status',)

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'barcode', 'email')
    ordering = ('last_name','first_name')
    search_fields = ('last_name','first_name', 'barcode')
    inlines = [AppointmentInline]

@admin.register(Items)
class ItemsAdmin(admin.ModelAdmin):
    list_display = ('title', 'pickuplocation', 'person', 'appointment')
    ordering = ('pickuplocation', 'person',)
    search_fields = ('person', 'pickuplocation')

class ItemsInline(admin.TabularInline):
    model = Items
    fields = ['title','library_name', 'location','call_number','status']
    readonly_fields = ('status',)

    def status(self,obj):
        return obj.get_item_status()



class BookingStatusFilter(admin.SimpleListFilter):
    title = 'Commande retirée' # a label for our filter
    parameter_name = 'booking_done' # you can put anything here

    def lookups(self, request, model_admin):
    # This is where you create filter options; we have two:
        return [
            ('done', 'Commande retirée'),
            ('not_done', 'Commande non retirée'),
        ] 

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        if self.value() == 'done':
            # Get websites that have at least one page.
            return queryset.distinct().filter(is_done=True)
        if self.value() == 'not_done':
            # Get websites that don't have any pages.
            return queryset.distinct().filter(is_done=False)
            
class PebStatusFilter(admin.SimpleListFilter):
    title = 'Demande de PEB' # a label for our filter
    parameter_name = 'peb' # you can put anything here

    def lookups(self, request, model_admin):
    # This is where you create filter options; we have two:
        return [
            ('peb', 'Demandes de peb'),
            ('not_peb', 'Hors demandes de PEB'),
        ] 

    def queryset(self, request, queryset):
    # This is where you process parameters selected by use via filter options:
        if self.value() == 'peb':
        # Get websites that have at least one page.
            return queryset.distinct().filter(is_peb=True)
        if self.value() == 'not_peb':
        # Get websites that don't have any pages.
            return queryset.distinct().filter(is_peb=False)



@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('date', 'library','person','get_number_of_items','is_done', 'is_peb')
    list_filter = ['date','library', BookingStatusFilter, PebStatusFilter]
    fields = ('date','library','user_formated','is_done', 'is_peb')
    readonly_fields = ['user_formated', 'library']
    inlines = [ItemsInline]

    def get_urls(self):

        # get the default urls
        urls = super(AppointmentAdmin, self).get_urls()

        # define security urls
        security_urls = [
            path('add/', self.admin_site.admin_view(self.add_rdv_form)),
            path('confirm/<str:pickup_loc_id>/<str:user_id>/', self.admin_site.admin_view(self.add_rdv_choose)),
            path('confirm_peb/<str:pickup_loc_id>/<str:user_id>', self.admin_site.admin_view(self.add_rdv_peb_choose)),
            # path('truc/', self.admin_site.admin_view(self.truc)),
            path('add_rdv/<str:pickup_loc_id>/<str:user_id>/<str:date_rdv>', self.admin_site.admin_view(self.rdv)),
            path('add_rdv_peb/<str:pickup_loc_id>/<str:user_id>/<str:date_rdv>', self.admin_site.admin_view(self.rdv_peb))
            # Add here more urls if you want following same logic
        ]

        # Make sure here you place your added urls first than the admin default urls
        return security_urls + urls

    # Your view definition fn
    def add_rdv_form(self, request):
        if request.method == 'POST':
            # create a  instance and populate it with data from the request:
            form = AddRdvForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
                user_id = form.cleaned_data['id_lecteur']
                libary_id = form.cleaned_data['library']
                is_peb = form.cleaned_data['is_peb']
                if is_peb :
                     return HttpResponseRedirect('/admin/cart_management/appointment/confirm_peb/{}/{}'.format(libary_id,user_id))
                else :
                     return HttpResponseRedirect('/admin/cart_management/appointment/confirm/{}/{}'.format(libary_id,user_id))
            # return HttpResponseRedirect('/admin/cart_management/appointment/confirm/{}/{}/{}'.format(libary_id,user_id,is_peb))

        # if a GET (or any other method) we'll create a blank form
        else:
            form = AddRdvForm()

        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            something="test",
            form=form
        )
        return TemplateResponse(request, "admin/add_rdv.html", context)

    def add_rdv_choose(self, request, pickup_loc_id, user_id):
        # Include common variables for rendering the admin template.
        library = PickupLocation.objects.get(name=pickup_loc_id)
        error, lecteur = services_request.get_user_info(user_id,library.institution)
        if error :
            messages.error(request, 'Utilisateur inconnu.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        error, user_carts = services_request.get_user_carts_admin(lecteur,library.institution,library.id_alma)
        if error :
            messages.error(request, 'Pas de réservations.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        if not user_carts :
            messages.error(request, 'Pas de réservations.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        user_requests_list = user_carts[library.id_alma]["user_request_list"]
        lecteur.save()
        resas = services_rdv.Resas(library,library.open_hour,library.close_hour, library.plot_number,library.handling_time,library.days_for_booking,admin=True)
        list_hours = resas.get_list_hours_for_public_view()
        print(list_hours)
        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            locals = locals()
        )
        
        return TemplateResponse(request, "admin/choose_rdv.html",context)
    
    def add_rdv_peb_choose(self, request, pickup_loc_id, user_id):
        # Include common variables for rendering the admin template.
        peb = True
        library = PickupLocation.objects.get(name=pickup_loc_id)
        error, lecteur = services_request.get_user_info(user_id,library.institution)
        if error :
            messages.error(request, 'Utilisateur inconnu.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        lecteur.save()
        resas = services_rdv.Resas(library,library.open_hour,library.close_hour, library.plot_number,library.handling_time,library.days_for_booking,admin=True)
        list_hours = resas.get_list_hours_for_public_view()
        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            locals = locals()
        )
        
        return TemplateResponse(request, "admin/choose_rdv.html",context)

    def rdv(self,request, pickup_loc_id, user_id, date_rdv):
        date_rdv_in_date = datetime.strptime(date_rdv, '%Y-%m-%d %H:%M:%S')
        # date_rdv_in_date = date_rdv
        pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
        error, user = services_request.get_user_info(user_id,pickup_loc.institution)
        if error :
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        ##On raffraichi et récupère la liste des résa du lecteur pour la bib
        error,title_list = services_request.refresh_user_request(user,pickup_loc)
        if error :
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        # On créé un rdv pour l'usager
        appointment = Appointment(date=date_rdv, person=user, library=pickup_loc)
        try:
            appointment.save()
        except IntegrityError as e: 
            if 'UNIQUE constraint' in e.args[0]:
                messages.error(request, "Cette plage vient d'être réservée par un autre utilisateur. Merci d'en choisir une nouvelle")
                return HttpResponseRedirect('/admin/cart_management/appointment/confirm/{}/{}'.format(pickup_loc_id,user_id))
            else:
                messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
                return HttpResponseRedirect('/admin/cart_management/appointment/confirm/{}/{}'.format(pickup_loc_id,user_id)) 
        except Exception as e:
            logger.error('Erreur : {}'.format(e))
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return HttpResponseRedirect('/admin/cart_management/appointment/confirm/{}/{}'.format(pickup_loc_id,user_id)) 
        #1 - On va marquer dans Alma les résas comme traité en ajoutant une note et une date de fin d'intéret + on attache notre rdv à la résa
        services_request.update_user_request(appointment,title_list,pickup_loc.institution)
        # for title in title_list 
        #2 - On envoi un mail à l'usager
        plain_message = loader.render_to_string("cart_management/user_mail_message.txt", locals())
        send_mail(
            "{} : Votre demande de Clique et collecte est validée pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
            plain_message,
            pickup_loc.from_email,
            [user.email],
            fail_silently=False,
        )
        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            locals = locals()
        )
        messages.success(request, 'Le rendez-vosu a été créé avec succès.')
        return HttpResponseRedirect("/admin/cart_management/appointment/?library__id_alma__exact={}".format(pickup_loc_id))

    def rdv_peb(self,request, pickup_loc_id, user_id, date_rdv):
        date_rdv_in_date = datetime.strptime(date_rdv, '%Y-%m-%d %H:%M:%S')
        # date_rdv_in_date = date_rdv
        pickup_loc = PickupLocation.objects.get(id_alma=pickup_loc_id)
        error, user = services_request.get_user_info(user_id,pickup_loc.institution)
        if error :
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        # On créé un rdv pour l'usager
        appointment = Appointment(date=date_rdv, person=user, library=pickup_loc,is_peb=True)
        try:
            appointment.save()
        except IntegrityError as e: 
            if 'UNIQUE constraint' in e.args[0]:
                messages.error(request, "Cette plage vient d'être réservée par un autre utilisateur. Merci d'en choisir une nouvelle")
                return HttpResponseRedirect('/admin/cart_management/appointment/confirm_peb/{}/{}'.format(pickup_loc_id,user_id)) 
            else:
                messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
                return HttpResponseRedirect('/admin/cart_management/appointment/confirm_peb/{}/{}'.format(pickup_loc_id,user_id)) 
        except Exception as e:
            logger.error('Erreur : {}'.format(e))
            messages.error(request, 'Un problème est survenu merci de rééssayer ou de contacter le support. [A REPRENDRE]')
            return HttpResponseRedirect('/admin/cart_management/appointment/confirm_peb/{}/{}'.format(pickup_loc_id,user_id)) 
        # for title in title_list 
        #2 - On envoi un mail à l'usager
        plain_message = loader.render_to_string("cart_management/user_mail_message.txt", locals())
        send_mail(
            "{} : Votre demande de Clique et collecte est validée pour le {}".format(pickup_loc.name,appointment.get_date_formatee('complet')),
            plain_message,
            pickup_loc.from_email,
            [user.email],
            fail_silently=False,
        )
        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            locals = locals()
        )
        messages.success(request, 'Le rendez-vosu a été créé avec succès.')
        return HttpResponseRedirect("/admin/cart_management/appointment/?library__id_alma__exact={}".format(pickup_loc_id))
        

    def user_formated(self, obj):
        return format_html('{} -- {} - <a href="mailto:{}">{}</a>', obj.person.full_name, obj.person.barcode,obj.person.email,obj.person.email)
    user_formated.short_description = format_html('<b><span class="glyphicon glyphicon-user"></span> Lecteur</b>')





class StaffInline(admin.StackedInline):
    model = Staff
    can_delete = False
    verbose_name_plural = 'Bibliothèque'
# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = [StaffInline]

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# class WeekDaysInline(admin.TabularInline):
#     model = DaysOfWeek


@admin.register(PickupLocation)
class PickupLocationAdmin(admin.ModelAdmin):
    list_display = ('id_alma', 'name','plot_number','handling_time','get_opening_days','open_hour','close_hour','mid_day_break','days_for_booking','email','message')
    filter_horizontal = ('opening_days','closed_days')
    # inlines = [WeekDaysInline]