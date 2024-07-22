from django.conf import settings
from .models import Employee,OTP
from django.core.mail import EmailMessage
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
import logging
from random import randint
import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class EmailBackend(SMTPBackend):
    @cached_property
    def ssl_context(self):
        if self.ssl_certfile or self.ssl_keyfile:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            return ssl_context
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context


def send_forget_password_OTP(request):
    req_email = request.POST.get('email')
    emp = Employee.objects.filter(email__iexact=req_email).first()
    if(emp):
        #Delete all previuse OTPs from the same email before creating a new one
        OTP.objects.filter(Email__iexact=req_email).delete()

        randomOTP = str(randint(100000, 999999))
        otpObj = OTP(OTP=randomOTP,Email=req_email)
        otpObj.save()
        send_email(emp.email,"Calendarinho OTP",randomOTP,request)
        

    else:
        print("'Forget password' with wrong email: "+req_email)


def send_email(recipient_email, subject, otp, request):
    print("Email sent to: "+recipient_email)
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [recipient_email,]
    context = {
                'otp': otp,
                'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                'domain' : settings.DOMAIN,
            }
    email_body = loader.render_to_string(
            'CalendarinhoApp/emails/otp_message.html', context)
    email = EmailMessage(subject, email_body, to=recipient_list)
    email.content_subtype = "html"
    try:
        email.send()
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

