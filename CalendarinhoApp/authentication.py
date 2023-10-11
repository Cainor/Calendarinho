from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render
from django.template import loader
from django.http import HttpResponseRedirect
from .models import Employee, OTP
from .forms import *
from django.views.decorators.csrf import csrf_exempt  # To Disable CSRF
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.contrib.auth.forms import PasswordResetForm
import logging
from django.conf import settings
from .email import send_forget_password_OTP
from threading import Thread

# Get an instance of a logger
logger = logging.getLogger(__name__)



def loginForm(request, next=''):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = Login_Form(request.POST)
        # check whether it's valid:
        if form.is_valid():
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = user = authenticate(username=username, password=password)
            if user and user.is_active:
                login(request, user)
                next_url = request.POST.get('next', '')
                if next_url and next_url.startswith('/'):
                    return HttpResponseRedirect(next_url)
                else:
                    return HttpResponseRedirect(reverse('CalendarinhoApp:Dashboard'))
            else:
                messages.error(request, "Invalid login details given")
                form = Login_Form()
                return render(request, 'CalendarinhoApp/login.html', {'form': form})

    # if a GET (or any other method) we'll create a blank form
    else:
        form = Login_Form()
        return render(request, 'CalendarinhoApp/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('CalendarinhoApp:login'))

def reset_password(email, from_email,
        template='CalendarinhoApp/emails/new_user_password_reset_email.html'):
    """
    Reset the password for an (active) user with given E-Mail address
    """
    form = PasswordResetForm({'email': email})
    if form.is_valid():
        return form.save(from_email=from_email, html_email_template_name=template,email_template_name=template, domain_override=settings.DOMAIN, use_https=settings.USE_HTTPS)


def forgetPasswordInit(request):
    form = passwordforgetInitForm()
    return render(request,"CalendarinhoApp/forgetpasswordInit.html",{"form": form})

def forgetpasswordOTP(request):
    if (request.method == 'POST'):
        #A thread to send an email in the background. Otherwise we will have an email enumeration using time-based attack.
        thread = Thread(target = send_forget_password_OTP, args= (request,))
        thread.start()
        form = passwordforgetEndForm()
        emp_mail = request.POST.get("email")
        return render(request,"CalendarinhoApp/forgetpasswordOTP.html",{"form":form,"emp_mail":emp_mail})
    else:
        return HttpResponseRedirect("/login/")

def forgetpasswordEnd(request):
    if (request.method == 'POST'):
        emp_mail = request.POST.get("emp_mail")
        form = passwordforgetEndForm(request.POST)

        fromDatabase = OTP.objects.filter(Email=emp_mail).first()
        if(not fromDatabase):
            messages.error(request, "Something is Wrong!")
            return render(request,"CalendarinhoApp/forgetpasswordOTP.html",{"form":form,"emp_mail":emp_mail})

        if(fromDatabase.OTP == request.POST.get("OTP") and int(fromDatabase.Tries) <= 5 and fromDatabase.now_diff() < 300):
            if form.is_valid():
                emp = Employee.objects.filter(email=emp_mail).first()
                emp.set_password(request.POST.get("new_Password"))
                emp.save()

                fromDatabase.delete()


                notifyAfterPasswordReset(emp)

                messages.success(request, "Password Changed Successfully!")
                Login_form = Login_Form()
                return render(request,"CalendarinhoApp/login.html",{"form":Login_form})
            else:
                return render(request,"CalendarinhoApp/forgetpasswordOTP.html",{"form":form,"emp_mail":emp_mail})
        else:
            messages.error(request, "Something went wrong!")

            #Increase number of tries:
            fromDatabase.Tries = str(int(fromDatabase.Tries)+1)

            fromDatabase.save()
            return render(request,"CalendarinhoApp/forgetpasswordOTP.html",{"form":form,"emp_mail":emp_mail})
    else:
        return HttpResponseRedirect("/login/")

def notifyAfterPasswordReset(user):
    """Send email to the user after password reset."""

    context = {
                'username': user.username,
                'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                'domain' : settings.DOMAIN,
            }
    email_body = loader.render_to_string(
            'CalendarinhoApp/emails/password_reset_complete_email.html', context)
    email = EmailMessage('Calendarinho password reset', email_body, to=[user.email])
    email.content_subtype = "html"
    try:
        thread = Thread(target = email.send, args= ())
        thread.start()
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))