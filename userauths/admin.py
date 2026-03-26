from django.contrib import admin
from userauths.models import User, Profile
# Register your models here.
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'email', 'full_name']
    list_display = [ 'username', 'email', 'full_name', 'phone','gender']


class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'full_name']
    list_display = ['user', 'full_name', 'verified']

admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
