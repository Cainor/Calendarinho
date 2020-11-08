from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from .models import CustomUser
from CalendarinhoApp.views import notifyAfterPasswordReset

class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class MySetPasswordForm(SetPasswordForm):
    def save(self, commit=True):
        """Overwrite 'SetPasswordForm' to send email to the user after password reset."""

        password_before = getattr(self.user, "password")
        super().save(commit=True)
        password_after = getattr(self.user, "password")
        if password_before != password_after:
            notifyAfterPasswordReset(self.user,domain="Calendarinho", protocol="https")
