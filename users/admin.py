# users/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext, gettext_lazy as _
from threading import Thread

from .models import CustomUser
from CalendarinhoApp.authentication import reset_password
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User
from django.conf import settings



class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'user_type', 'is_active']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
         'fields': ('first_name', 'last_name', 'email', 'user_type')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'date_quit')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'user_type'),
        }),
    )
    search_fields = ('username', 'first_name', 'last_name', 'user_type')

    def save_model(self, request, obj, form, change):
        """Save new user and send a notification to the user to reset his password."""
        super().save_model(request, obj, form, change)
        if not change:
            email = request.POST.getlist('email')
            thread = Thread(target = reset_password, args= (email[0], request))
            thread.start()

    # Load the current skills in the field
    def get_form(self, request, obj=None, **kwargs):
        return super(CustomUserAdmin, self).get_form(request, obj)

admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)