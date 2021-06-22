from CalendarinhoApp.models import Service
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from .models import CustomUser
from CalendarinhoApp.views import notifyAfterPasswordReset
from django.conf import settings

class CustomUserCreationForm(UserCreationForm):
    skillset = forms.ModelMultipleChoiceField(label='Skills', queryset=Service.objects.all(), required=False, help_text='Skillset')


    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class CustomUserChangeForm(UserChangeForm):
    skillset = forms.ModelMultipleChoiceField(label='Skills', queryset=Service.objects.all(), required=False, help_text='Skillset')

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'skillset')

class MySetPasswordForm(SetPasswordForm):
    def save(self, commit=True):
        """Overwrite 'SetPasswordForm' to send email to the user after password reset."""

        password_before = getattr(self.user, "password")
        super().save(commit=True)
        password_after = getattr(self.user, "password")
        if password_before != password_after:
            notifyAfterPasswordReset(self.user,domain="CHANGE IT", protocol="https")

