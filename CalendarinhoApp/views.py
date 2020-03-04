from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse, Http404, HttpResponseRedirect
from .models import Employee, Engagement, Leave
from .forms import EmployeeOverlapForm, Login_Form
from django.views.decorators.csrf import csrf_exempt  # To Disable CSRF
from django.http import JsonResponse
import datetime
import csv
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required



def not_found(request, exception=None):
    response = render(request, 'CalendarinhoApp/404.html', {})
    response.status_code = 404
    return response

@login_required
def Dashboard(request):
    emps = Employee.objects.exclude(user_type='M')

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
    context = {
        'statistics': statistics
    }
    # Add the form for Avalibality Calculation
    form = EmployeeOverlapForm()
    context.update({"form": form})
    return render(request, "CalendarinhoApp/Dashboard.html", context)

@login_required
def EmployeesTable(request):
    emps = Employee.objects.exclude(user_type='M')
    table = []
    row = {}
    for emp in emps:
        empstat = emp.currentStatus()
        row["empID"] = emp.id
        row["name"] = emp.first_name + " " +  emp.last_name
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
        # check if the user type "Manager"
        if emp.user_type == 'M':
            raise Employee.DoesNotExist
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
def engagement(request, eng_id):
    try:
        eng = Engagement.objects.get(id=eng_id)
        context = {'eng': eng}
    except Engagement.DoesNotExist:
        return not_found(request)
    return render(request, "CalendarinhoApp/engagement.html", context)

@login_required
def EngagementsCal(request):
    event_arr = Engagement.getAllEngs()
    context = {
        "events": event_arr,
    }
    return render(request, 'CalendarinhoApp/EngagementsCalendar.html', context)

@login_required
def overlap(request):
    emps = Employee.objects.exclude(user_type='M')
    avalibleEmps = {"emp": [],
                    "id": []}
    sdate = request.POST.get("Start_Date")
    edate = request.POST.get("End_Date")
    csdate = datetime.datetime.strptime(str(sdate), "%Y-%m-%d")
    cedate = datetime.datetime.strptime(str(edate), "%Y-%m-%d")

    if (cedate >= csdate):
        for emp in emps:
            if (not emp.overlapCheck(sdate, edate)):
                avalibleEmps["emp"].append(emp.first_name + " " + emp.last_name)
                avalibleEmps["id"].append(emp.id)
            else:
                pass
        return JsonResponse(avalibleEmps)
    else:
        return render(request, "CalendarinhoApp/EasterEgg.html", {})

def overlapPrecentage():
    emps = Employee.objects.exclude(user_type='M')
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
def exportCSV(request, empID=None):
    output = []
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)

    if (empID != None):  # Return all engagements for a single employee
        try:
            emp =  Employee.objects.filter(id=empID).first()
            # check if the user type "Manager"
            if emp.user_type == 'M':
                return not_found(request)
            query_set = Engagement.objects.filter(Employees=empID)
            empName = emp.username
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

    else:  # Return all engagements
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
            if user:
                if user.is_active:
                    login(request,user)                
                    if 'next' in request.POST:
                        return HttpResponseRedirect(request.POST.get('next'))
                    else:
                        return HttpResponseRedirect(reverse('CalendarinhoApp:Dashboard'))
                else:
                    return HttpResponse("Your account was inactive.")
            else:
                print("Someone tried to login and failed.")
                print("They used username: {} and password: {}".format(username,password))
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
