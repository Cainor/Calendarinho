from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.http import HttpResponse, Http404, HttpResponseRedirect
from .models import Employee, Engagement, Leave, Client, Comment, OTP
from .forms import *
from django.views.decorators.csrf import csrf_exempt  # To Disable CSRF
from django.http import JsonResponse
import datetime
import csv
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.mail import EmailMessage
from django.contrib.auth.forms import PasswordResetForm
import logging
from django.shortcuts import resolve_url
from django.conf import settings
from datetime import timedelta, date
import calendar
import os


# Get an instance of a logger
logger = logging.getLogger(__name__)

from .MZemail import send_forget_password_OTP
from threading import Thread
from django.db.models import Q 
from autocomplete.forms import EmployeeCounter

utilizationFilePath =  os.path.join(os.path.dirname(os.path.dirname(__file__)),"UtilizationChartIput.txt")


def not_found(request, exception=None):
    response = render(request, 'CalendarinhoApp/404.html', {})
    response.status_code = 404
    return response


@login_required
def Dashboard(request):

    # calculateUtilizationToFile(2020)
    # calculation for utilization chart
    try:
        f = open(utilizationFilePath, "r")
        utilizationList = []
        for line in f:
            utilizationList.append(int(line))
    except Exception as e:
        logger.error("Failed to calculate utilization: \n" + str(e))


    emps = Employee.objects.exclude(is_active=False)

    # calculation for pie chart
    state = {}
    state['avalible'] = 0
    state['engaged'] = 0
    state['training'] = 0
    state['vacation'] = 0
    for emp in emps:
        empstat = emp.currentStatus()[0]
        if (empstat == 'Available'):
            state['avalible'] += 1
        elif (empstat == 'Engaged'):
            state['engaged'] += 1
        elif (empstat == 'Training'):
            state['training'] += 1
        elif (empstat == 'Vacation'):
            state['vacation'] += 1

    # calculation fot the engagements card (bars)
    engs = Engagement.objects.all()
    engsTable = []
    singleEng = {}
    for eng in engs:
        precent = eng.daysLeftPrecentage()
        if(precent != "Nope"):
            singleEng['engid'] = eng.id
            singleEng['engName'] = eng.EngName
            singleEng['precent'] = precent
            engsTable.append(singleEng.copy())
    engsTable = sorted(engsTable, key=lambda i: i['precent'])

    # Statistics
    statistics = {}
    # Number of engagement that has EndDate greater than or equal today.
    statistics['upcomingEngagements'] = Engagement.objects.filter(
        StartDate__gt=str(datetime.date.today())).count()
    statistics['ongoingEngagements'] = Engagement.objects.filter(StartDate__lte=str(datetime.date.today())).filter(
        EndDate__gte=str(datetime.date.today())).count()  # Number of engagement that has EndDate greater than or equal today.
    # Precentage of available employees
    statistics['availabilityPercentage'] = overlapPrecentage()
    statistics['numberOfEmployees'] = emps.count()  # Number of Employees
    statistics['pieChartStatus'] = state
    statistics['engagementsBars'] = engsTable
    if utilizationList:
        statistics['2020UtilizationChart'] = utilizationList
    context = {
        'statistics': statistics
    }
    # Add the form for Avalibality Calculation
    form = EmployeeOverlapForm()
    context.update({"form": form})
    return render(request, "CalendarinhoApp/Dashboard.html", context)


@login_required
def EmployeesTable(request):
    emps = Employee.objects.exclude(is_active=False)
    table = []
    row = {}
    for emp in emps:
        empstat = emp.currentStatus()
        row["empID"] = emp.id
        row["name"] = emp.first_name + " " + emp.last_name
        if (empstat[0] == "Available"):
            row["status"] = empstat[0]
        else:
            row["status"] = empstat[0] + ": " + empstat[1]
        row["endDate"] = empstat[2]
        empnextev = emp.nextEvent()
        row["nextev"] = empnextev[0]
        row["startDate"] = empnextev[1]
        table.append(row.copy())

    context = {
        'table': table
    }
    return render(request, "CalendarinhoApp/EmployeesTable.html", context)


@login_required
def EngagementsTable(request):
    engs = Engagement.objects.all()
    table = []
    row = {}
    for eng in engs:
        row["engID"] = eng.id
        row["name"] = eng.EngName
        row["clientName"] = eng.CliName
        row["serviceType"] = eng.ServiceType
        row["endDate"] = eng.EndDate
        row["startDate"] = eng.StartDate
        table.append(row.copy())

    context = {
        'table': table
    }
    return render(request, "CalendarinhoApp/EngagementsTable.html", context)


@login_required
def profile(request, emp_id):
    try:
        emp = Employee.objects.get(id=emp_id)
        upcoming = {}
        upcoming["engagement"] = Engagement.objects.filter(Employees=emp_id).filter(
            StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("StartDate").first()
        upcoming["vacation"] = Leave.objects.filter(emp_id=emp_id).filter(StartDate__gt=datetime.datetime.now(
        ).strftime("%Y-%m-%d")).filter(LeaveType="Vacation").order_by("StartDate").first()
        upcoming["training"] = Leave.objects.filter(emp_id=emp_id).filter(StartDate__gt=datetime.datetime.now(
        ).strftime("%Y-%m-%d")).filter(LeaveType="Training").order_by("StartDate").first()
        leaves = emp.getAllLeaves()
        engagements = emp.getAllEngagements()

        context = {"emp": emp,
                   "lev": leaves,
                   "engs": engagements,
                   "upcoming": upcoming}

    except Employee.DoesNotExist:
        return not_found(request)
    return render(request, "CalendarinhoApp/profile.html", context)


@login_required
def client(request, cli_id):
    try:
        cli = Client.objects.get(id=cli_id)

        engs = Engagement.objects.filter(CliName_id=cli_id)

        context = {'cli': cli,
                   'engs': engs}
    except Client.DoesNotExist:
        return not_found(request)

    return render(request, "CalendarinhoApp/client.html", context)


@login_required
def ClientsTable(request):
    clients = Client.objects.all()
    table = []
    row = {}
    for cli in clients:
        row["cliID"] = cli.id
        row["name"] = cli.CliName
        row["acronym"] = cli.CliShort
        row["code"] = cli.CliCode
        table.append(row.copy())

    context = {
        'table': table
    }
    return render(request, "CalendarinhoApp/ClientsTable.html", context)


@login_required
def engagement(request, eng_id):
    engagement = Engagement.objects.get(id=eng_id)
    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Create Comment object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # Assign the current engagement to the comment
            new_comment.eng = engagement
            # Assign the current user to the comment
            new_comment.user = request.user
            # Save the comment to the database
            new_comment.save()
            # Send notification to the users those involved in the engagement
            thread = Thread(target = notifyNewComment, args= (new_comment, request))
            thread.start()     
    try:
        comment_form = CommentForm()
        comments = Comment.objects.filter(eng_id=engagement.id)
        context = {'eng': engagement, 'scope_list': engagement.Scope.split('\n'),'comment_form': comment_form,
                   'comments': comments}
    except Engagement.DoesNotExist:
        return not_found(request)
    return render(request, "CalendarinhoApp/engagement.html", context)


@login_required
def deleteMyComment(request, commentID):
    try:
        comment = Comment.objects.get(id=commentID)
    except Comment.DoesNotExist:
        return not_found(request)
    if(comment.user == request.user or request.user.user_type == "M"):
        comment.delete()
        return HttpResponseRedirect("/engagement/"+str(comment.eng.id))
    else:
        return not_found(request)


@login_required
def EngagementsCal(request):
    event_arr = Engagement.getAllEngs()
    context = {
        "events": event_arr,
    }
    return render(request, 'CalendarinhoApp/EngagementsCalendar.html', context)


@login_required
def EmployeesCal(request):
    leaves = {}
    engagements = Engagement.objects.none()
    selectedEmps = []
    if request.method == 'POST':
        listemp = request.POST.getlist('emps')
        for empID in listemp:
            selectedEmps.append(Employee.objects.get(id=empID))
        # Leaves
        for empID in listemp:
            emp = Employee.objects.get(id=empID)
            leaves.update(
                {emp.first_name+" "+emp.last_name: emp.getAllLeaves()})

        # Engagements
        for empID in listemp:
            emp = Employee.objects.get(id=empID)
            engagements = engagements | emp.Engagements.all()
        engagements = engagements.distinct()  # Remove Doublicate
    emps = Employee.objects.all().exclude(is_active=False).order_by('first_name')
    return render(request, 'CalendarinhoApp/EmployeesCalendar.html', {'employees': emps, 'leaves': leaves, 'engagements': engagements, 'selectedEmps': selectedEmps})


@login_required
def overlap(request):
    emps = Employee.objects.exclude(is_active=False).order_by('first_name')
    avalibleEmps = {"emp": [],
                    "id": []}
    sdate = request.POST.get("Start_Date")
    edate = request.POST.get("End_Date")
    csdate = datetime.datetime.strptime(str(sdate), "%Y-%m-%d")
    cedate = datetime.datetime.strptime(str(edate), "%Y-%m-%d")

    if (cedate >= csdate):
        for emp in emps:
            if (not emp.overlapCheck(sdate, edate)):
                avalibleEmps["emp"].append(
                    emp.first_name + " " + emp.last_name)
                avalibleEmps["id"].append(emp.id)
            else:
                pass
        return JsonResponse(avalibleEmps)
    else:
        return render(request, "CalendarinhoApp/EasterEgg.html", {})


def overlapPrecentage():
    emps = Employee.objects.exclude(is_active=False)
    count = 0
    todayDate = datetime.date.today()

    for emp in emps:
        if (not emp.overlapCheck(todayDate, todayDate)):
            count += 1
        else:
            pass
    try:
        return "{:2.0f}%".format(100-(100*(count/emps.count())))
    except ZeroDivisionError:
        return "100%"


@login_required
def exportCSV(request, empID=None, slug=None):
    output = []
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    if(slug == "Clients"):
        query_set = Client.objects.all()
        response['Content-Disposition'] = u'attachment; filename="{0}"'.format(
            "All-Clients.csv")  # Name of the file
        # Header
        writer.writerow(['Client Name', 'Acronym', 'Client Code'])
        for cli in query_set:
            output.append([cli.CliName, cli.CliShort, cli.CliCode])
        # CSV Data
        writer.writerows(output)
        return response
    elif (slug == "Enagemgents"):  # Return all engagements
        query_set = Engagement.objects.all()
        response['Content-Disposition'] = u'attachment; filename="{0}"'.format(
            "All-Engagements.csv")  # Name of the file
        # Header
        writer.writerow(['Name', 'Client', 'Service Type',
                         'Start Date', 'End Date'])
        for eng in query_set:
            output.append([eng.EngName, eng.CliName,
                           eng.ServiceType, eng.StartDate, eng.EndDate])
        # CSV Data
        writer.writerows(output)
        return response
    elif (empID != None):  # Return all engagements for a single employee
        try:
            emp = Employee.objects.filter(id=empID).first()
            query_set = Engagement.objects.filter(Employees=empID)
            empName = emp.first_name + '-' + emp.last_name
            response['Content-Disposition'] = u'attachment; filename="{0}"'.format(
                empName.replace(" ", "-")+".csv")  # Name of the file
            # Header
            writer.writerow(['Name', 'Client', 'Service Type',
                             'Start Date', 'End Date'])
            for eng in query_set:
                output.append([eng.EngName, eng.CliName,
                               eng.ServiceType, eng.StartDate, eng.EndDate])
            # CSV Data
            writer.writerows(output)
            return response
        except:
            return not_found(request)
    else:
        return not_found(request)


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
                if 'next' in request.POST:
                    return HttpResponseRedirect(request.POST.get('next'))
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


def notifyEngagedEmployees(empsBefore, empsAfter, engagement, request):
    """Send emails to employees when he added or removed from engagement."""

    #Check the users added to the engagement
    addedEmps = []
    if empsAfter is None:
        addedEmps = []
    elif empsBefore is None :
        addedEmps = empsAfter
    else:
        addedEmps=empsAfter.exclude(id__in=empsBefore)

    #Check the users removed from the engagement
    removedEmps = []
    if empsBefore is None:
        removedEmps= []
    elif empsAfter is None :
        removedEmps = empsBefore
    else:
        removedEmps=empsBefore.exclude(id__in=empsAfter)

    emails = []
    #Send email to the added users
    for addedEmp in addedEmps :
        context = {
                'first_name': addedEmp.first_name,
                'message': str(request.user) + ' has assigned you to a new engagement',
                'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                    args=[engagement.id])),
                'engagement_name': engagement.EngName,
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,
            }
        email_body = loader.render_to_string(
            'CalendarinhoApp/emails/employee_engagement_email.html', context)
        email = EmailMessage('You have been engaged', email_body, to=[addedEmp.email])
        email.content_subtype = "html"
        emails.append(email)

    #Send email to the removed users
    for removedEmp in removedEmps :
        context = {
                'first_name': removedEmp.first_name,
                'message': str(request.user) + ' has removed you from an engagement ',
                'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                    args=[engagement.id])),
                'engagement_name': engagement.EngName,
                'engagement_strDate':engagement.StartDate,
                'engagement_endDate':engagement.EndDate,
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,
            }
        email_body = loader.render_to_string(
            'CalendarinhoApp/emails/employee_engagement_email.html', context)
        email = EmailMessage('You have been unengaged', email_body, to=[removedEmp.email])
        email.content_subtype = "html"
        emails.append(email)
    try:
        connection = mail.get_connection()
        connection.send_messages(emails)
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

def notifyNewComment(comment, request):
    user = comment.user
    engagement = comment.eng
    employees= engagement.Employees.all()
    emails = []
    for employee in employees :
        # check if the comment is by the employee him or herself
        if user == employee:
            continue
        context = {
                'first_name': employee.first_name,
                'message': 'New comment on your engagement by ' + user.first_name + ' ' + user.last_name + '.',
                'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                    args=[engagement.id])),
                'engagement_name': engagement.EngName,
                'user':user,
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,
            }
        email_body = loader.render_to_string(
            'CalendarinhoApp/emails/engagement_comment_email.html', context)
        email = EmailMessage('New comment on your engagement', email_body, to=[employee.email])
        email.content_subtype = "html"
        emails.append(email)
    try:
        connection = mail.get_connection()
        connection.send_messages(emails)
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

def reset_password(email, from_email, domain,
        template='CalendarinhoApp/emails/new_user_password_reset_email.html'):
    """
    Reset the password for all (active) users with given E-Mail address
    """
    form = PasswordResetForm({'email': email})
    if form.is_valid():
        return form.save(from_email=from_email, html_email_template_name=template,email_template_name=template, domain_override=domain, use_https=False)

def notifyAfterPasswordReset(user, request=None, domain=None, protocol=None):
    """Send email to the user after password reset."""

    context = {
                'username': user.username,
                'protocol': 'http', #CHANGE IT IN PRODUCTION
                'domain' : get_current_site(request).domain if request else domain,
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

def notifyManagersNewEngagement(user, engagement, request):
    """Send notifications to the managers after a new engagement is added."""
    
    managers = Employee.getManagers()
    emails = []
    for manager in managers :
        context = {
                'first_name': manager.first_name,
                'message': 'New engagement added by ' + user.first_name + ' ' + user.last_name + '.',
                'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                    args=[engagement.id])),
                'engagement_name': engagement.EngName,
                'user':user,
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,                
            }
        email_body = loader.render_to_string(
            'CalendarinhoApp/emails/manager_new_engagement_email.html', context)
        email = EmailMessage('New engagement added', email_body, to=[manager.email])
        email.content_subtype = "html"
        emails.append(email)
    try:
        connection = mail.get_connection()
        connection.send_messages(emails)
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

def notifyManagersNewLeave(user, leave , request):
    """Send notifications to the managers after a new leave is added."""
    
    managers = Employee.getManagers()
    emails = []
    for manager in managers :
        forEmployee = leave.emp.first_name + ' ' + leave.emp.last_name
        addBy = user.first_name + ' ' + user.last_name
        if leave.emp == user :
              forEmployee = 'him or herself'
        if leave.emp == manager:
              forEmployee = 'you'
        if user == manager:
            addBy = 'you'
        if user == manager == leave.emp:
            addBy = 'you'
            forEmployee = 'yourself'
        context = {
                'first_name': manager.first_name,
                'message': 'New leave added by ' + addBy
                    + ' for ' + forEmployee,
                'leave_type': leave.LeaveType,
                'start_date': leave.StartDate,
                'end_date': leave.EndDate,
                'note': leave.Note,
                'Employee': leave.emp.first_name + ' ' + leave.emp.last_name,
                'profile_url': request.build_absolute_uri(reverse('CalendarinhoApp:profile',
                    args=[leave.emp.id])),
                'protocol': 'https' if request.is_secure() else 'http',
                'domain' : get_current_site(request).domain,
            }
        email_body = loader.render_to_string(
            'CalendarinhoApp/emails/manager_new_leave_email.html', context)
        email = EmailMessage('New leave added', email_body, to=[manager.email])
        email.content_subtype = "html"
        emails.append(email)
    try:
        connection = mail.get_connection()
        connection.send_messages(emails)
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

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


                notifyAfterPasswordReset(emp, request=request)

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

@login_required
def counterEmpSvc(request):
    #Only Managers and Superusers are allowed
    if(not request.user.is_superuser and not request.user.user_type == 'M'):
        return not_found(request)
    else:
        form = EmployeeCounter()
        if (request.method == 'GET'):
            countList = {}
            for emp in Employee.objects.all().order_by('first_name'):
                empCount = []
                for srv in Service.objects.all():
                    empCount.append(emp.countSrv(srv.id))
                countList.update({emp:empCount})
            
            serviceList = Service.objects.all()
            return render(request,"CalendarinhoApp/counterEmpSvc.html",{'form':form, 'countList':countList, 'serviceList':serviceList})
        else:
            countList = {}
            
            if(not request.POST.get("Employees")):
                for emp in Employee.objects.all().order_by('first_name'):
                    countList.update({emp:''})
            else:
                empInputList = request.POST.getlist("Employees")
                for empID in empInputList:
                    emp = Employee.objects.get(id=empID)
                    countList.update({emp:''})
            
            serviceList = []
            if(not request.POST.get("ServiceType")):
                for serv in Service.objects.all():
                    serviceList.append(serv)
            else:
                servInputList = request.POST.getlist("ServiceType")
                for serv in servInputList:
                    serviceList.append(Service.objects.get(id=serv))
            
            for emp in countList:
                countSrvList = []
                for serv in serviceList:
                    countSrvList.append(emp.countSrv(serv.id))
                countList.update({emp:countSrvList})

            return render(request,"CalendarinhoApp/counterEmpSvc.html",{'form':form, 'countList':countList, 'serviceList':serviceList})


def employeesUtilization(start_date, end_date):

    
    """ Calculate employees utilization in a specific period of time """

    if not (isinstance(start_date, datetime.date) and isinstance(end_date, datetime.date)):
        raise Exception("Sorry, start date and end date should be date objects")
    totalUtilization = 0
    numberOFDays = 0
    for single_date in daterange(start_date, end_date):
        numberOFDays += 1
        dayUtilization = 0
        employees_in_that_day = Employee.objects.filter(date_joined__lt = (single_date + timedelta(days=1)) ).exclude(is_active=False)
        utilized_employees = []
        for employee in employees_in_that_day:
            if employee.overlapCheck(single_date,single_date):
                utilized_employees.append(employee)
        try:
            dayUtilization = len(utilized_employees) / employees_in_that_day.count()
        except ZeroDivisionError as e:
            logger.error("Number of employees in " + str(single_date) + " is zero so utilization will be zero: \n" + str(e))
            dayUtilization = 0
        totalUtilization += dayUtilization
    totalUtilization = totalUtilization / numberOFDays
    return totalUtilization


def daterange(start_date, end_date):
    """ Rturn dates range in a specific period of time  """
    for n in range(int((end_date - start_date).days)+1):
        yield start_date + timedelta(n)

def monthesStartAndEndDates(year):
    """ Return a list containing the start date and end date for each month in a specific year """
    result = []
    for i in range(12):
        startdate = date(int(year), i+1, 1).replace(day=1) 
        enddate = date(int(year), i+1, calendar.monthrange(int(year), i+1)[1])
        result.append((startdate, enddate))
    return result


def calculateUtilizationToFile(year):
    try:
        f = open(utilizationFilePath)
        # Do something with the file
    except IOError:
        try:
            f = open(utilizationFilePath, "w")
            monthsDates = monthesStartAndEndDates(year)
            first= True
            for i in range(len(monthsDates)):
                utilization = employeesUtilization(monthsDates[i][0], monthsDates[i][1])
                if not first:
                    f.write("\n")
                first = False
                f.write(str((int(100 * (round(utilization,2))))))
        except Exception as e:
            logger.error("Failed to calculate utilization: \n" + str(e))
    finally:
        f.close()

def toggleTheme(request):
    response = redirect("/Dashboard")
    year_inSeconds = 31536000
    if (not request.COOKIES.get("theme")):
        response.set_cookie("theme","Dark",max_age=year_inSeconds)
    elif (request.COOKIES.get("theme") == "Dark"):
        response.set_cookie("theme","Light",max_age=year_inSeconds)
    else:
        response.set_cookie("theme","Dark",max_age=year_inSeconds)
    return response


def ResourceAssignment(request):
        #Only Managers and Superusers are allowed
    if(not request.user.is_superuser and not request.user.user_type == 'M'):
        return not_found(request)
    else:
        form = ResourceManagment()
        if (request.method == 'GET'):
            return render(request,"CalendarinhoApp/ResourceAssignment.html",{"form":form})
        
        else:
            form = ResourceManagment(data=request.POST)
            countList = {}
            # Check if emp has the skill
            emps = Employee.objects.exclude(username="aalnogaithan").exclude(user_type__in=['D']).order_by('first_name').exclude(is_active=False).filter(SkilledEmployees=request.POST.get("servList"))

            # Check if emp is avalible
            sdate = request.POST.get("start_date")
            edate = request.POST.get("end_date")
            empsAvail = []
            for emp in emps:
                if (not emp.overlapCheck(sdate,edate)):
                    empsAvail.append(emp)
            # Count eng with the same service
            for emp in empsAvail:

                countList[emp] = emp.countSrv(request.POST.get("servList"))
            # Order by less count
            sortedArray = sorted(countList.items(), key=lambda x: x[1])
            countList = {}
            for obj in sortedArray:
                key, val = obj
                countList[key] = val

            
            return render(request,"CalendarinhoApp/ResourceAssignment.html",{"countList":countList,"form":form})