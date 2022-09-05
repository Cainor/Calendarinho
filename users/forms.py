from CalendarinhoApp.models import Service
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from .models import CustomUser
from CalendarinhoApp.authentication import notifyAfterPasswordReset

class MySetPasswordForm(SetPasswordForm):
    def save(self, commit=True):
        """Overwrite 'SetPasswordForm' to send email to the user after password reset."""

        password_before = getattr(self.user, "password")
        super().save(commit=True)
        password_after = getattr(self.user, "password")
        if password_before != password_after:
            notifyAfterPasswordReset(self.user,domain="Calendarinho.example.com", protocol="https")

