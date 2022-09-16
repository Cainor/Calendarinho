
from threading import Thread
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render
from django.template import loader
from .models import Employee, Engagement, Leave, ProjectManager
from .forms import *
from django.http import JsonResponse
import datetime
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.mail import EmailMessage
import logging
from django.conf import settings
from datetime import timedelta
from .forms import LeaveForm

# Get an instance of a logger
logger = logging.getLogger(__name__)

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
    emps = Employee.objects.exclude(is_active=False).order_by('first_name')
    return render(request, 'CalendarinhoApp/EmployeesCalendar.html', {'employees': emps, 'leaves': leaves, 'engagements': engagements, 'selectedEmps': selectedEmps})


@login_required
def overlap(request):
    emps = Employee.objects.order_by('first_name').exclude(is_active=False)
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

@login_required
def overlapPrecentage(request):
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
def LeaveCreate(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        
        if form.is_valid():
            obj = form.save(commit=False)
            obj.emp = request.user
            obj.save()
            # Send notifications to the managers after a new leave is added.
            thread = Thread(target = notifyManagersNewLeave, args= (request.user, obj, request))
            thread.start()  
            result = {"status": True}
            return JsonResponse(result)
    
    result = {"status": False}
    return JsonResponse(result, status=500)

@login_required
def LeavesCal(request):
    allEmps = Employee.objects.all()
    leaves = {}
    for emp in allEmps:
        leaves.update({emp.first_name + " " + emp.last_name: emp.getAllLeaves()})
    return render(request, 'CalendarinhoApp/LeavesCalendar.html', {'leaves':leaves})



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
                'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                'domain' : settings.DOMAIN,
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

    
@login_required
def projectManager(request, projmgr_id):
    projmgr = ProjectManager.objects.get(id=projmgr_id)
    return render(request,"CalendarinhoApp/ProjectManager.html",{"projmgr":projmgr})

from .views import not_found, daterange
