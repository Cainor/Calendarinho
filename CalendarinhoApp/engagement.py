from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from .models import Employee, Engagement, Comment, Reports
from .forms import *
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.mail import EmailMessage
import logging
from django.conf import settings

# Get an instance of a logger
logger = logging.getLogger(__name__)

from threading import Thread
from .views import not_found


@login_required
def EngagementCreate(request):
    if request.method == 'POST':
        form = EngagementForm(request.POST)
        if form.is_valid():
            form.save()
            result = {"status": True}
            return JsonResponse(result)
    
    result = {"status": False}
    return JsonResponse(result, status=500)


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
            return HttpResponseRedirect("/engagement/"+str(engagement.id))
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
def uploadReport(request, eng_id):
        context = {}
        eng = Engagement.objects.get(id=eng_id)
        form = uploadReportForm()
        listReports = Reports.objects.filter(eng=eng)
        context['engagement'] = eng
        context['form'] = form
        context['list'] = listReports

        if request.method == 'POST':
                form = uploadReportForm(request.POST, request.FILES)
                if form.is_valid():
                    Report = Reports(eng=eng, user=request.user,reportType=request.POST["reportType"],note=request.POST["note"], file=request.FILES['file'])
                    Report.save()
                    thread = Thread(target = notifyNewReportUpload, args= (Report, request))
                    thread.start()   
                    
                    context['reference']=Report.reference
                    context['note'] = Report.note
                    return render(request,'CalendarinhoApp/UploadReports.html',context)
                else:
                    context['error'] = "Only .gpg files are allowed"
                    return render(request,'CalendarinhoApp/UploadReports.html',context)
        else:
            return render(request,'CalendarinhoApp/UploadReports.html',context)


@login_required
def downloadReport(request, refUUID=None):
    report = Reports.objects.get(reference=refUUID)
    if(report != None): #Check if UUID is correct
        response = HttpResponse(report.file, content_type='application/pgp-encrypted')
        filename=report.file.name
        response['Content-Disposition'] = 'attachment; filename=%s' % (filename) #Filename
        return response
    else:
        return not_found(request)


@login_required
def deleteReport(request, refUUID=None):
    report = Reports.objects.get(reference=refUUID)
    if(report != None): #Check if UUID is correct
        if(request.user.is_superuser or request.user==report.user):
            eng_id = report.eng.id
            report.delete()
            return redirect("/engagement/"+str(eng_id)+"/Reports/")
        else:
            return not_found(request)
    else:
        return not_found(request)


def notifyEngagedEmployees(empsBefore, empsAfter, engagement, request):
    """Send emails to employees when he added or removed from engagement."""

    # Convert empsAfter to a set of integers
    empsAfter = set(map(int, empsAfter))
    empsBefore = set(empsBefore)

    # Check the users added to the engagement
    addedEmps = Employee.objects.filter(id__in=empsAfter - empsBefore)


    # Check the users removed from the engagement
    removedEmps = Employee.objects.filter(id__in=empsBefore - empsAfter)

    
    #Send email to the added users
    try:
        with mail.get_connection() as connection:
            for addedEmp in addedEmps :
                context = {
                        'first_name': addedEmp.first_name,
                        'message': str(request.user) + ' has assigned you to a new engagement',
                        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                            args=[engagement.id])),
                        'engagement_name': engagement.EngName,
                        'StartDate': engagement.StartDate,
                        'EndDate': engagement.EndDate,
                        'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                        'domain' : settings.DOMAIN,
                    }
                email_body = loader.render_to_string(
                    'CalendarinhoApp/emails/employee_engagement_email.html', context)
                email = EmailMessage('You have been engaged', email_body, to=[addedEmp.email], connection=connection)
                email.content_subtype = "html"
                email.send()

            #Send email to the removed users
            for removedEmp in removedEmps :
                context = {
                        'first_name': removedEmp.first_name,
                        'message': str(request.user) + ' has removed you from an engagement ',
                        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                            args=[engagement.id])),
                        'engagement_name': engagement.EngName,
                        'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                        'domain' : settings.DOMAIN,
                    }
                email_body = loader.render_to_string(
                    'CalendarinhoApp/emails/employee_engagement_removed_email.html', context)
                email = EmailMessage('You have been unengaged', email_body, to=[removedEmp.email], connection=connection)
                email.content_subtype = "html"
                email.send()

    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))

def notifyNewComment(comment, request):
    user = comment.user
    engagement = comment.eng
    employees= engagement.Employees.exclude(id=user.id)
    context = {
        'message': f'New comment on your engagement by {user.get_full_name()}.',
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.EngName,
        'user': user,
        'commentbody': comment.body,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }
    try:
        with get_connection() as connection:
            for employee in employees :
                context = {
                        'first_name': employee.first_name,
                        'message': 'New comment on your engagement by ' + user.first_name + ' ' + user.last_name + '.',
                        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                            args=[engagement.id])),
                        'engagement_name': engagement.EngName,
                        'user':user,
                        'commentbody':comment.body,
                        'protocol': 'https' if settings.USE_HTTPS == True else 'http',
                        'domain' : settings.DOMAIN,
                    }
                email_body = loader.render_to_string(
                    'CalendarinhoApp/emails/engagement_comment_email.html', context)
                email = EmailMessage('New comment on your engagement', email_body, to=[employee.email], connection=connection)
                email.content_subtype = "html"
                email.send()
    except ConnectionRefusedError as e:
        logger.error("Failed to send emails: \n" + str(e))


def notifyNewReportUpload(report, request):
    uploader = request.user
    engagement = report.eng
    employees = engagement.Employees.exclude(id=uploader.id)

    context = {
        'first_name': uploader.first_name,
        'message': f'New report uploaded on your engagement by {uploader.get_full_name()}.',
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.EngName,
        'reportType': report.reportType,
        'user': uploader,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }

    try:
        with get_connection() as connection:
            for employee in employees:
                email_body = render_to_string(
                    'CalendarinhoApp/emails/engagement_comment_uploadReport.html', 
                    {**context, 'recipient_first_name': employee.first_name}
                )
                email = EmailMessage(
                    'New report uploaded on your engagement',
                    email_body,
                    to=[employee.email],
                    connection=connection
                )
                email.content_subtype = "html"
                email.send()
            
    except ConnectionRefusedError as e:
        logger.error(f"Failed to send emails: {e}")

def notifyManagersNewEngagement(user, engagement, request):
    """Send notifications to the managers after a new engagement is added."""
    
    managers = Employee.getManagers()

    base_context = {
        'message': f'New engagement added by {user.get_full_name()}.',
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.EngName,
        'user': user,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }

    try:
        with get_connection() as connection:
            for manager in managers:
                context = {**base_context, 'first_name': manager.first_name}
                
                email_body = render_to_string(
                    'CalendarinhoApp/emails/manager_new_engagement_email.html', 
                    context
                )
                
                email = EmailMessage(
                    'New engagement added',
                    email_body,
                    to=[manager.email],
                    connection=connection
                )
                email.content_subtype = "html"
                
                email.send()  # Send each email individually

    except ConnectionRefusedError as e:
        logger.error(f"Failed to send emails: {e}")
