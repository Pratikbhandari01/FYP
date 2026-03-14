from django.contrib import admin
from .models import Booking, Hotel
from hotel.models import HotelGallery, HotelFeatures, Hotelfaqs, RoomType,ActivityLog


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'name', 'location', 'status', 'featured', 'date']
    prepopulated_fields = {'slug': ('name',)} 

admin.site.register(HotelGallery)
admin.site.register(Booking)
admin.site.register(HotelFeatures)
admin.site.register(Hotelfaqs)
admin.site.register(RoomType)
admin.site.register(ActivityLog)