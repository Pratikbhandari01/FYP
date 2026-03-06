from django.contrib import admin
from .models import Hotel


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'name', 'location', 'status', 'featured', 'date']
    prepopulated_fields = {'slug': ('name',)} 