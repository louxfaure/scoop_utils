from django.contrib import admin
from django.utils.html import format_html
from .models import PickupLocation,Person,Items, Appointment


admin.site.site_title = "Gestion du Click and Collect "
admin.site.site_header = "Gestion du Click and Collect"
admin.site.index_title = "Gestion du Click and Collect"


admin.site.register(PickupLocation)

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


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('date', 'library','person','done')
    list_filter = ['date','library','done']
    fields = ['date','library','user_formated','done']
    readonly_fields = ['user_formated', 'library']
    inlines = [ItemsInline]

    def user_formated(self, obj):
        return format_html('{} -- {} - <a href="mailto:{}">{}</a>', obj.person.full_name, obj.person.barcode,obj.person.email,obj.person.email)
    user_formated.short_description = format_html('<b><span class="glyphicon glyphicon-user"></span> Lecteur</b>')