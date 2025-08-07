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

logger = logging.getLogger(__name__)
from autocomplete.forms import EmployeeCounter
from .employee import overlapPrecentage

def not_found(request, exception=None):
    response = render(request, 'CalendarinhoApp/404.html', {})
    response.status_code = 404
    return response

@login_required
def Dashboard(request):
    # Use optimized service functions for better performance
    from .service import get_dashboard_summary
    
    # Get optimized statistics
    dashboard_stats = get_dashboard_summary()
    
    # Legacy engagement progress data (keep for compatibility)
    engs = Engagement.objects.select_related('client').filter(
        start_date__lte=datetime.date.today(),
        end_date__gte=datetime.date.today()
    )
    engsTable = []
    cliTable = {}
    
    for eng in engs:
        precent = eng.days_left_percentage()
        if precent != "Nope":
            singleEng = {
                'engid': eng.id,
                'engName': eng.name,
                'precent': precent,
                'start_date': eng.start_date,
                'end_date': eng.end_date
            }
            engsTable.append(singleEng)
            cliTable[eng.client] = eng.client.count_current_engagements()
    
    engsTable = sorted(engsTable, key=lambda i: i['precent'])
    cliTable = {k: v for k, v in sorted(cliTable.items(), key=lambda item: item[1], reverse=True)}
    
    # Enhanced statistics with optimized data
    statistics = {
        'upcomingEngagements': dashboard_stats['engagements']['upcoming'],
        'ongoingEngagements': dashboard_stats['engagements']['ongoing'],
        'completedEngagements': dashboard_stats['engagements']['completed'],
        'availabilityPercentage': overlapPrecentage(request),
        'numberOfEmployees': dashboard_stats['employees']['total'],
        'teamUtilization': dashboard_stats['utilization'],
        'activeClients': dashboard_stats['clients']['active'],
        'totalClients': dashboard_stats['clients']['total'],
        'pieChartStatus': {
            'available': dashboard_stats['employees']['available'],
            'engaged': dashboard_stats['employees']['engaged'],
            'training': dashboard_stats['employees']['training'],
            'vacation': dashboard_stats['employees']['vacation']
        },
        'engagementsBars': engsTable,
        'cliBars': cliTable
    }
    
    context = {'statistics': statistics}
    form = EmployeeOverlapForm()
    context.update({"form": form})
    return render(request, "CalendarinhoApp/Dashboard.html", context)

@login_required
def managerDashboard(request):
    if(not request.user.is_superuser and not request.user.user_type == 'M'):
        return not_found(request)
    else:
        # Import enhanced dashboard function
        from .service import get_enhanced_manager_dashboard_data
        
        form = countEngDays()
        emps = Employee.objects.exclude(is_active=False)

        if (request.method == 'GET'):
            eDate = datetime.date.today()
            sDate = eDate - timedelta(days=90)
            form = countEngDays(initial={'start_date': sDate,'end_date':eDate})

            # ENHANCED: Get comprehensive dashboard data
            enhanced_data = get_enhanced_manager_dashboard_data(sDate, eDate)

            # LEGACY: Maintain backward compatibility for existing template
            # Use enhanced data when available, fallback to legacy calculation
            if enhanced_data['success']:
                empsNumDays = enhanced_data['enhanced_emp_data']
            else:
                # Fallback to legacy calculation
                empsNumDays = []
                for emp in emps:
                    result = []
                    noDays = emp.countEngDays(sDate, eDate)
                    result.append(emp)
                    result.append(noDays)
                    empsNumDays.append(result)
                empsNumDays.sort(key=lambda x:x[1])
            
            # Calculate the total number of working days for all emps for specific time period
            allEmpDays = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                allEmpDays.append(noDays)
            allEmpDays = sum(allEmpDays)

            # Calculate the cost based on total numbers of emps working days in specific period of time 
            allEmpDaysCost = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                cost = noDays * settings.COST_PER_DAY
                allEmpDaysCost.append(cost)
            allEmpDaysCost = sum(allEmpDaysCost)

            # Get client overview data
            from .models import Client
            client_overview_list = []
            clients = Client.objects.all()
            for client in clients:
                today = datetime.date.today()
                active_engagements = client.engagements.filter(
                    start_date__lte=today, end_date__gte=today
                ).count()
                
                # Get vulnerability summary
                vuln_summary = client.get_vulnerability_summary()
                open_vulnerabilities = vuln_summary.get('total_open', 0)
                
                client_overview_list.append({
                    'name': client.name,
                    'active_engagements': active_engagements,
                    'open_vulnerabilities': open_vulnerabilities,
                    'needs_attention': open_vulnerabilities > 0 or active_engagements == 0
                })

            # ENHANCED: Build comprehensive context with new analytics
            context = {
                # Legacy variables (keep for backward compatibility)
                'empsNumDays': empsNumDays,
                'allEmpDays': allEmpDays,
                'allEmpDaysCost': "{:,}".format(allEmpDaysCost),
                'form': form,
                
                # NEW: Enhanced performance metrics
                'team_utilization': enhanced_data.get('team_utilization', 0),
                'monthly_revenue': "{:,}".format(enhanced_data.get('monthly_revenue', 0)),
                'client_health_score': enhanced_data.get('client_health_score', 0),
                'available_capacity': enhanced_data.get('available_capacity', 0),
                'cost_per_emp_per_day': enhanced_data.get('cost_per_emp_per_day', settings.COST_PER_DAY),
                'budget_variance': enhanced_data.get('budget_variance', 0),
                'total_services': enhanced_data.get('total_services', 0),
                'total_employees': emps.count(),
                
                # NEW: Action required data
                'action_alerts': enhanced_data.get('action_alerts', []),
                'underutilized_count': enhanced_data.get('underutilized_count', 0),
                'team_capacity': enhanced_data.get('team_utilization', 0),
                'inactive_clients': enhanced_data.get('inactive_clients', 0),
                'critical_vulns': enhanced_data.get('critical_vulns', 0),
                'total_open_vulnerabilities': enhanced_data.get('total_open_vulnerabilities', 0),
                
                # NEW: Enhanced chart data and analytics
                'employee_performance_data': enhanced_data.get('enhanced_emp_data', empsNumDays),
                'financial_summary': enhanced_data.get('financial_summary', {}),
                'utilization_distribution': enhanced_data.get('utilization_distribution', {}),
                'client_overview': client_overview_list,
                
                # NEW: Quick actions data
                'quick_actions': [
                    {'title': 'Review Under-utilized Team', 'url': '#', 'icon': 'fa-users', 'count': enhanced_data.get('underutilized_count', 0)},
                    {'title': 'Address Critical Vulnerabilities', 'url': '#', 'icon': 'fa-exclamation-triangle', 'count': enhanced_data.get('critical_vulns', 0)},
                    {'title': 'Client Relationship Review', 'url': '#', 'icon': 'fa-handshake', 'count': enhanced_data.get('inactive_clients', 0)},
                    {'title': 'Capacity Planning', 'url': '#', 'icon': 'fa-calendar-alt', 'count': 1 if enhanced_data.get('team_utilization', 0) > 85 else 0}
                ],
                
                # NEW: Success indicator for debugging
                'enhanced_data_success': enhanced_data.get('success', False),
                'calculation_error': enhanced_data.get('error', None) if not enhanced_data.get('success', False) else None
            }
            return render(request,"CalendarinhoApp/managerDashboard.html",context)
        
        else:
            form = countEngDays(data=request.POST)

            sDate_str = request.POST.get("start_date")
            eDate_str = request.POST.get("end_date")
            
            # Convert string dates to date objects
            try:
                sDate = datetime.datetime.strptime(sDate_str, '%Y-%m-%d').date() if sDate_str else datetime.date.today() - timedelta(days=90)
                eDate = datetime.datetime.strptime(eDate_str, '%Y-%m-%d').date() if eDate_str else datetime.date.today()
            except ValueError:
                sDate = datetime.date.today() - timedelta(days=90)
                eDate = datetime.date.today()

            # ENHANCED: Get comprehensive dashboard data with form dates
            enhanced_data = get_enhanced_manager_dashboard_data(sDate, eDate)

            # LEGACY: Maintain backward compatibility
            if enhanced_data['success']:
                empsNumDays = enhanced_data['enhanced_emp_data']
            else:
                empsNumDays = []
                for emp in emps:
                    result = []
                    noDays = emp.countEngDays(sDate, eDate)
                    result.append(emp)
                    result.append(noDays)
                    empsNumDays.append(result)
                empsNumDays.sort(key=lambda x:x[1])
            
            # Calculate the total number of working days for all emps for specific time period
            allEmpDays = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                allEmpDays.append(noDays)
            allEmpDays = sum(allEmpDays)

            # Calculate the cost - use different calculation for POST (legacy behavior)
            allEmpDaysCost = []
            for emp in emps:
                noDays = emp.countEngDays(sDate, eDate)
                cost = (noDays * 8) * 1200  # Legacy POST calculation
                allEmpDaysCost.append(cost)
            allEmpDaysCost = sum(allEmpDaysCost)

            # ENHANCED: Build comprehensive context with form submission data
            context = {
                # Legacy variables (keep for backward compatibility)
                'empsNumDays': empsNumDays,
                'allEmpDays': allEmpDays,
                'allEmpDaysCost': "{:,}".format(allEmpDaysCost),
                'form': form,
                
                # NEW: Enhanced performance metrics with custom date range
                'team_utilization': enhanced_data.get('team_utilization', 0),
                'monthly_revenue': "{:,}".format(enhanced_data.get('monthly_revenue', 0)),
                'client_health_score': enhanced_data.get('client_health_score', 0),
                'available_capacity': enhanced_data.get('available_capacity', 0),
                'cost_per_emp_per_day': enhanced_data.get('cost_per_emp_per_day', settings.COST_PER_DAY),
                'budget_variance': enhanced_data.get('budget_variance', 0),
                
                # NEW: Action required data
                'action_alerts': enhanced_data.get('action_alerts', []),
                'underutilized_count': enhanced_data.get('underutilized_count', 0),
                'team_capacity': enhanced_data.get('team_utilization', 0),
                'inactive_clients': enhanced_data.get('inactive_clients', 0),
                'critical_vulns': enhanced_data.get('critical_vulns', 0),
                
                # NEW: Enhanced chart data and analytics
                'employee_performance_data': enhanced_data.get('enhanced_emp_data', empsNumDays),
                'financial_summary': enhanced_data.get('financial_summary', {}),
                'utilization_distribution': enhanced_data.get('utilization_distribution', {}),
                
                # NEW: Quick actions data
                'quick_actions': [
                    {'title': 'Review Under-utilized Team', 'url': '#', 'icon': 'fa-users', 'count': enhanced_data.get('underutilized_count', 0)},
                    {'title': 'Address Critical Vulnerabilities', 'url': '#', 'icon': 'fa-exclamation-triangle', 'count': enhanced_data.get('critical_vulns', 0)},
                    {'title': 'Client Relationship Review', 'url': '#', 'icon': 'fa-handshake', 'count': enhanced_data.get('inactive_clients', 0)},
                    {'title': 'Capacity Planning', 'url': '#', 'icon': 'fa-calendar-alt', 'count': 1 if enhanced_data.get('team_utilization', 0) > 85 else 0}
                ],
                
                # NEW: Success indicator for debugging
                'enhanced_data_success': enhanced_data.get('success', False),
                'calculation_error': enhanced_data.get('error', None) if not enhanced_data.get('success', False) else None
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
            output.append([cli.name, cli.acronym, cli.code])
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
            output.append([eng.name, eng.client,
                           eng.service_type, eng.start_date, eng.end_date])
        # CSV Data
        writer.writerows(output)
        return response
    elif (empID != None):  # Return all engagements for a single employee
        try:
            emp = Employee.objects.filter(id=empID).first()
            query_set = Engagement.objects.filter(employees=empID)
            empName = emp.first_name + '-' + emp.last_name
            response['Content-Disposition'] = u'attachment; filename="{0}"'.format(
                empName.replace(" ", "-")+".csv")  # Name of the file
            # Header
            writer.writerow(['Name', 'Client', 'Service Type',
                             'Start Date', 'End Date','JiraURL'])
            for eng in query_set:
                output.append([eng.name, eng.client,
                               eng.service_type, eng.start_date, eng.end_date, getattr(eng, 'JiraURL', '')])
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
            
            if(not request.POST.get("employees")):
                for emp in Employee.objects.all().order_by('first_name'):
                    countList.update({emp:''})
            else:
                empInputList = request.POST.getlist("employees")
                for empID in empInputList:
                    emp = Employee.objects.get(id=empID)
                    countList.update({emp:''})
            
            serviceList = []
            if(not request.POST.get("service_type")):
                for serv in Service.objects.all():
                    serviceList.append(serv)
            else:
                servInputList = request.POST.getlist("service_type")
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

def debug_inline(request):
    """Debug page for inline editing issues"""
    return render(request, 'CalendarinhoApp/debug_inline.html')
