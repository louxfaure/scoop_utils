from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin import ModelAdmin, SimpleListFilter
from .models import PickupLocation,Person,Items, Appointment,Staff, DaysOfWeek


admin.site.site_title = "Gestion du Click and Collect "
admin.site.site_header = "Gestion du Click and Collect"
admin.site.index_title = "Gestion du Click and Collect"

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
    list_display = ('date', 'library','person','is_done')
    list_filter = ['date','library', BookingStatusFilter]
    fields = ('date','library','user_formated','is_done')
    readonly_fields = ['user_formated', 'library']
    inlines = [ItemsInline]

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
class PickupLocation(admin.ModelAdmin):
    filter_horizontal = ('opening_days',)
    # inlines = [WeekDaysInline]