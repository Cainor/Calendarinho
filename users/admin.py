# users/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext, gettext_lazy as _
from threading import Thread

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from CalendarinhoApp.views import reset_password
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User
from django.conf import settings



class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'user_type', 'is_active']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
         'fields': ('first_name', 'last_name', 'email', 'user_type', 'user_level','skillset')}),
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

        # Here we save the skillset
        if change:
            obj.SkilledEmployees.clear()
            for skill in form.cleaned_data['skillset']:
                obj.SkilledEmployees.add(skill)
            obj.save()


        super().save_model(request, obj, form, change)
        if not change:
            email = request.POST.getlist('email')

            # Get site domain 
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
            thread = Thread(target = reset_password, args= (email[0], settings.EMAIL_HOST_USER,request))
            thread.start()

    # Load the current skills in the field
    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.form.base_fields['skillset'].initial = obj.SkilledEmployees.all()
        return super(CustomUserAdmin, self).get_form(request, obj)

admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)
