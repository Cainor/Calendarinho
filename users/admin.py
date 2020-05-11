# users/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext, gettext_lazy as _

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from CalendarinhoApp.views import reset_password
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'user_type']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
         'fields': ('first_name', 'last_name', 'email', 'user_type')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
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

            # Get site domain 
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain

            reset_password(email=email[0], from_email='Calendarinho' , domain=domain)


admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)