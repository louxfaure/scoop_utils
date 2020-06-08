from django.contrib import admin
from .models import PickupLocation,Person,Items, Appointment

admin.site.register(PickupLocation)
admin.site.register(Person)


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
    list_display = ('date', 'library','person',)
    list_filter = ['date','library']
    inlines = [ItemsInline]