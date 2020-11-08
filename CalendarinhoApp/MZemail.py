from django.conf import settings
from .models import Employee,OTP
from django.core.mail import EmailMessage
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site

import logging

from random import randint

logger = logging.getLogger(__name__)

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
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,
            }
    email_body = loader.render_to_string(
            'CalendarinhoApp/emails/otp_message.html', context)
    email = EmailMessage(subject, email_body, to=recipient_list)
    email.content_subtype = "html"
    try:
        email.send()
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

