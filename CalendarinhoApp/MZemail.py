from django.conf import settings
from django.core.mail import send_mail
from .models import Employee,OTP
from random import randint


def send_forget_password_OTP(request):
    req_email = request.POST.get('email')
    emp = Employee.objects.filter(email=req_email).first()
    if(emp):
        #Delete all previuse OTPs from the same email before creating a new one
        OTP.objects.filter(Email=req_email).delete()

        randomOTP = str(randint(100000, 999999))
        otpObj = OTP(OTP=randomOTP,Email=req_email)
        otpObj.save()
        send_email(emp.email,"Calendarinho OTP",randomOTP)
        

    else:
        print("'Forget password' with wrong email: "+req_email)


def send_email(recipient_email, subject, message):
    print("Email sent to: "+recipient_email)
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [recipient_email,]
    send_mail( subject, message, email_from, recipient_list )
    print("Sent")

