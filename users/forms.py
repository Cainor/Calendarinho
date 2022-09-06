from django.contrib.auth.forms import SetPasswordForm
from CalendarinhoApp.authentication import notifyAfterPasswordReset
from django.conf import settings


class MySetPasswordForm(SetPasswordForm):
    def save(self, commit=True):
        """Overwrite 'SetPasswordForm' to send email to the user after password reset."""

        password_before = getattr(self.user, "password")
        super().save(commit=True)
        password_after = getattr(self.user, "password")
        if password_before != password_after:
            notifyAfterPasswordReset(self.user,domain=settings.DOMAIN, protocol="https" if settings.USE_HTTPS == True else "http")

