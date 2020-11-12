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
from .models import PickupLocation,Person,Items, Appointment,Staff,DaysOfWeek
from django.template.response import TemplateResponse
from .services import services_request, services_rdv
from .forms import NameForm
# from security.models import Security

admin.site.site_title = "Gestion du Clic et Collecte "
admin.site.site_header = "Gestion du Clic et Collecte"
admin.site.index_title = "Gestion du Clic et Collecte"

admin.site.register(DaysOfWeek)
# admin.site.register(PickupLocation)


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



@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('date', 'library','person','get_number_of_items','is_done')
    list_filter = ['date','library', BookingStatusFilter]
    fields = ('date','library','user_formated','is_done')
    readonly_fields = ['user_formated', 'library']
    inlines = [ItemsInline]

    def get_urls(self):

        # get the default urls
        urls = super(AppointmentAdmin, self).get_urls()

        # define security urls
        security_urls = [
            url(r'^add/$', self.admin_site.admin_view(self.add_rdv_form)),
            url(r'^confirm/$', self.admin_site.admin_view(self.add_rdv_choose))
            url(r'^rdv/$', self.admin_site.admin_view(self.rdv))
            # Add here more urls if you want following same logic
        ]

        # Make sure here you place your added urls first than the admin default urls
        return security_urls + urls

    # Your view definition fn
    def add_rdv_form(self, request):
        if request.method == 'POST':
            # create a form instance and populate it with data from the request:
            form = NameForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
                return HttpResponseRedirect('/thanks/')

        # if a GET (or any other method) we'll create a blank form
        else:
            form = NameForm()

        context = dict(
            self.admin_site.each_context(request), # Include common variables for rendering the admin template.
            something="test",
            form=form
        )
        return TemplateResponse(request, "admin/add_rdv.html", context)

    def add_rdv_choose(self, request):
        self.admin_site.each_context(request), # Include common variables for rendering the admin template.
        user_id = request.POST['id_lecteur']
        library = PickupLocation.objects.get(id_alma=request.POST['library'])
        error, lecteur = services_request.get_user_info(user_id,library.institution)
        if error :
            messages.error(request, 'Utilisateur inconnu.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        error, user_carts = services_request.get_user_carts_admin(lecteur,library.institution,request.POST['library'])
        if error :
            messages.error(request, 'Pas de réservations.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        if not user_carts :
            messages.error(request, 'Pas de réservations.')
            return HttpResponseRedirect('/admin/cart_management/appointment/add/')
        user_requests_list = user_carts[request.POST['library']]["user_request_list"]
        lecteur.save()
        resas = services_rdv.Resas(library,library.open_hour,library.close_hour, library.plot_number,library.handling_time,library.days_for_booking)
        list_hours = resas.get_list_hours_for_public_view()
        
        return TemplateResponse(request, "admin/choose_rdv.html",locals())
        

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
    filter_horizontal = ('opening_days',)
    # inlines = [WeekDaysInline]