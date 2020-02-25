from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse,Http404
from .models import Employee, Engagement, Leave
from .forms import EmployeeOverlapForm
from django.views.decorators.csrf import csrf_exempt #To Disable CSRF
from django.http import JsonResponse
import datetime

def Dashboard(request): #NEW STYLE
    emps = Employee.objects.all()
    
    #calculation for pie chart
    state = {}
    state['avalible'] = 0
    state['engaged'] = 0
    state['training'] = 0
    state['vacation'] = 0
    for emp in emps:
        empstat = emp.currentStatus()[0]
        if ( empstat == 'Available'):
            state['avalible'] += 1
        elif (empstat == 'Engaged'):
            state['engaged'] += 1
        elif (empstat == 'Training'):
            state['training'] += 1
        elif (empstat == 'Vacation'):
            state['vacation'] += 1

    #calculation fot the engagements card (bars)
    engs = Engagement.objects.all()
    engsTable = []
    singleEng = {}
    for eng in engs:
        precent = eng.daysLeft()
        if(precent != "Nope"):
            singleEng['engid'] = eng.id
            singleEng['engName'] = eng.EngName
            singleEng['precent'] = precent
            engsTable.append(singleEng.copy())
    engsTable = sorted(engsTable, key = lambda i: i['precent'])

    #Statistics
    statistics = {}
    statistics['upcomingEngagements'] = Engagement.objects.filter(StartDate__gt= str(datetime.date.today())).count() #Number of engagement that has EndDate greater than or equal today.
    statistics['ongoingEngagements'] = Engagement.objects.filter(StartDate__lte= str(datetime.date.today())).filter(EndDate__gte= str(datetime.date.today())).count() #Number of engagement that has EndDate greater than or equal today.
    statistics['availabilityPercentage'] = overlapPrecentage() #Precentage of available employees
    statistics['numberOfEmployees'] = emps.count() #Number of Employees
    statistics['pieChartStatus'] = state
    statistics['engagementsBars'] = engsTable
    context = { 
                'statistics': statistics
              }
    #Add the form for Avalibality Calculation
    form = EmployeeOverlapForm()
    context.update({"form":form})
    return render(request, "CalendarinhoApp/Dashboard.html", context)

def EmployeesTable(request): #NEW STYLE
    emps = Employee.objects.all()
    table = []
    row = {}
    for emp in emps:
        empstat = emp.currentStatus()
        row["empID"] = emp.id
        row["name"] = emp.EmpName
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


def EngagementsTable(request): #NEW STYLE
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



def profile(request, emp_id):
    try:
        emp = Employee.objects.get(id=emp_id)

        upcoming = {}
        upcoming["engagement"] = Engagement.objects.filter(Employees = emp_id).filter(StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("StartDate").first()
        upcoming["vacation"] = Leave.objects.filter(emp_id = emp_id).filter(StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).filter(LeaveType = "Vacation").order_by("StartDate").first()
        upcoming["training"] = Leave.objects.filter(emp_id = emp_id).filter(StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).filter(LeaveType = "Training").order_by("StartDate").first()
        print(upcoming)
        leaves = emp.getAllLeaves()
        engagements = emp.getAllEngagements()

        context = {"emp":emp,
                   "lev":leaves,
                   "engs":engagements,
                   "upcoming":upcoming}

    except Employee.DoesNotExist:
        raise Http404("Employee does not exist")
    return render(request,"CalendarinhoApp/profile.html",context)

def engagement(request, eng_id):
    try:
        eng = Engagement.objects.get(id=eng_id)
        context = { 'eng':eng }
    except Engagement.DoesNotExist:
        raise Http404("Engagement does not exist")
    return render(request,"CalendarinhoApp/engagement.html", context)


def EngagementsCal(request):
    event_arr = Engagement.getAllEngs()
    context = {
    "events":event_arr,
    }
    return render(request,'CalendarinhoApp/EngagementsCalendar.html',context)

def EmployeesCal(request):
    if request.method == 'POST':
        emp_ids = request.POST.getlist("myCheckboxes[]")

        engagements = []
        for i in emp_ids:
            emp = Employee.objects.get(id=i)
            engagements += emp.getAllEngagements()
        
        engagements = [i for n, i in enumerate(engagements) if i not in engagements[n + 1:]] #Remove duplicate engagements.
        leaves = {}
        for i in emp_ids:
            emp = Employee.objects.get(id=i)
            leaves.update({emp.EmpName:emp.getAllLeaves()})
        result = {"engagements":engagements,"leaves":leaves}
        print(result)
        return JsonResponse(result)
    try:
        emp = Employee.objects.all()
        context = {"employees":emp}
        form = EmployeeOverlapForm()
        context.update({"form":form})
    except Employee.DoesNotExist:
        raise Http404("Employee does not exist")
    return render(request,"CalendarinhoApp/EmployeesCalendar.html",context)

def overlap(request):
    emps = Employee.objects.all()
    avalibleEmps = {"emp":[],
                    "id":[]}
    sdate = request.POST.get("Start_Date")
    edate = request.POST.get("End_Date")
    csdate = datetime.datetime.strptime(str(sdate), "%Y-%m-%d")
    cedate = datetime.datetime.strptime(str(edate), "%Y-%m-%d")
    
    if (cedate >= csdate):
        for emp in emps:
            if (not emp.overlapCheck(sdate, edate)):
                avalibleEmps["emp"].append(emp.EmpName)
                avalibleEmps["id"].append(emp.id)
            else:
                pass
        return JsonResponse(avalibleEmps)
    else:
        return render(request,"CalendarinhoApp/EasterEgg.html",{})

def overlapPrecentage():
    emps = Employee.objects.all()
    count = 0
    todayDate = datetime.date.today()
    
    for emp in emps:
        if (not emp.overlapCheck(todayDate, todayDate)):
            count +=1
        else:
            pass
    try:
        return "{:2.0f}%".format(100-(100*(count/emps.count())))
    except ZeroDivisionError:
        return "100%"