from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Employee, Engagement, Client
from .forms import *
import datetime
import csv
from django.contrib.auth.decorators import login_required
import logging
from django.conf import settings
from datetime import timedelta, date
import calendar

# Get an instance of a logger
logger = logging.getLogger(__name__)

from autocomplete.forms import EmployeeCounter


from .employee import overlapPrecentage

# utilizationFilePath =  os.path.join(os.path.dirname(os.path.dirname(__file__)),"UtilizationChartIput.txt")

def not_found(request, exception=None):
    response = render(request, 'CalendarinhoApp/404.html', {})
    response.status_code = 404
    return response


@login_required
def Dashboard(request):

    # calculateUtilizationToFile(2020)
    # calculation for utilization chart
    # try:
    #     f = open(utilizationFilePath, "r")
    #     utilizationList = []
    #     for line in f:
    #         utilizationList.append(int(line))
    # except Exception as e:
    #     logger.error("Failed to calculate utilization: \n" + str(e))


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
    cliTable = {}
    singleEng = {}
    for eng in engs:
        precent = eng.daysLeftPrecentage()
        if(precent != "Nope"):
            singleEng['engid'] = eng.id
            singleEng['engName'] = eng.EngName
            singleEng['precent'] = precent
            engsTable.append(singleEng.copy())
            cliTable[eng.CliName] = eng.CliName.countCurrentEng()
    engsTable = sorted(engsTable, key=lambda i: i['precent'])

    # Sort for the new toggled view:
    cliTable = {k: v for k, v in sorted(cliTable.items(), key=lambda item: item[1],reverse=True)}

    # Statistics
    statistics = {}
    # Number of engagement that has EndDate greater than or equal today.
    statistics['upcomingEngagements'] = Engagement.objects.filter(
        StartDate__gt=str(datetime.date.today())).count()
    statistics['ongoingEngagements'] = Engagement.objects.filter(StartDate__lte=str(datetime.date.today())).filter(
        EndDate__gte=str(datetime.date.today())).count()  # Number of engagement that has EndDate greater than or equal today.
    # Precentage of available employees
    statistics['availabilityPercentage'] = overlapPrecentage(request)
    statistics['numberOfEmployees'] = emps.count()  # Number of Employees
    statistics['pieChartStatus'] = state
    statistics['engagementsBars'] = engsTable
    statistics['cliBars'] = cliTable
    # if utilizationList:
        # statistics['2020UtilizationChart'] = utilizationList
    context = {
        'statistics': statistics
    }
    # Add the form for Avalibality Calculation
    form = EmployeeOverlapForm()
    context.update({"form": form})
    return render(request, "CalendarinhoApp/Dashboard.html", context)

@login_required
def managerDashboard(request):
    if(not request.user.is_superuser and not request.user.user_type == 'M'):
        return not_found(request)
    else:
        form = countEngDays()
        emps = Employee.objects.exclude(is_active=False)

        if (request.method == 'GET'):
            eDate = datetime.date.today()
            sDate = eDate - timedelta(days=90)
            form = countEngDays(initial={'start_date': sDate,'end_date':eDate})

            # list for employees with less than 20% under the average working days
            empsNumDays = []
            for emp in emps:
                result = []
                noDays = emp.countEngDays(sDate, eDate)
                result.append(emp)
                result.append(noDays)
                empsNumDays.append(result)
            # sorting results by less emp days
            empsNumDays.sort(key=lambda x:x[1])
            
            # Calculate the total number of wroking days for all emps for specific time period
            allEmpDays = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                allEmpDays.append(noDays)
            allEmpDays = sum(allEmpDays)

            # Calculate the cost based on total numbers of emps working days in specific period of time 
            allEmpDaysCost = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                cost = noDays * 100 #Estimated Cost Per Day (Needs updating)
                allEmpDaysCost.append(cost)
            allEmpDaysCost = sum(allEmpDaysCost)

            context = {
                'empsNumDays': empsNumDays,
                'allEmpDays': allEmpDays,
                'allEmpDaysCost': "{:,}".format(allEmpDaysCost),
                "form":form
            }
            return render(request,"CalendarinhoApp/managerDashboard.html",context)
        
        else:
            form = countEngDays(data=request.POST)

            sDate = request.POST.get("start_date")
            eDate = request.POST.get("end_date")

            empsNumDays = []
            for emp in emps:
                result = []
                noDays = emp.countEngDays(sDate, eDate)
                result.append(emp)
                result.append(noDays)
                empsNumDays.append(result)
            # sorting results by less emp days
            empsNumDays.sort(key=lambda x:x[1])
            
            # Calculate the total number of wroking days for all emps for specific time period
            allEmpDays = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                allEmpDays.append(noDays)
            allEmpDays = sum(allEmpDays)

            # Calculate the cost based on total numbers of emps working days in specific period of time 
            allEmpDaysCost = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                cost = (noDays * 8) * 1200
                allEmpDaysCost.append(cost)
            allEmpDaysCost = sum(allEmpDaysCost)


            context = {
                'empsNumDays': empsNumDays,
                'allEmpDays': allEmpDays,
                'allEmpDaysCost': "{:,}".format(allEmpDaysCost),
                'form': form
            }
            return render(request, "CalendarinhoApp/managerDashboard.html", context)

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
                             'Start Date', 'End Date','JiraURL'])
            for eng in query_set:
                output.append([eng.EngName, eng.CliName,
                               eng.ServiceType, eng.StartDate, eng.EndDate, eng.JiraURL])
            # CSV Data
            writer.writerows(output)
            return response
        except:
            return not_found(request)
    else:
        return not_found(request)


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


# def calculateUtilizationToFile(year):
#     try:
#         f = open(utilizationFilePath)
#         # Do something with the file
#     except IOError:
#         try:
#             f = open(utilizationFilePath, "w")
#             monthsDates = monthesStartAndEndDates(year)
#             first= True
#             for i in range(len(monthsDates)):
#                 utilization = employeesUtilization(monthsDates[i][0], monthsDates[i][1])
#                 if not first:
#                     f.write("\n")
#                 first = False
#                 f.write(str((int(100 * (round(utilization,2))))))
#         except Exception as e:
#             logger.error("Failed to calculate utilization: \n" + str(e))
#     finally:
#         f.close()

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
