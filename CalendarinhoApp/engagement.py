from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from .models import Employee, Engagement, Comment, Report, Vulnerability
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
        row["name"] = eng.name
        row["clientName"] = eng.client
        row["serviceType"] = eng.service_type
        row["endDate"] = eng.end_date
        row["startDate"] = eng.start_date
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
        comments = Comment.objects.filter(engagement_id=engagement.id)
        context = {'eng': engagement, 'scope_list': engagement.scope.split('\n'),'comment_form': comment_form,
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
    event_arr = Engagement.get_all_engagements()
    context = {
        "events": event_arr,
    }
    return render(request, 'CalendarinhoApp/EngagementsCalendar.html', context)


@login_required
def uploadReport(request, eng_id):
        context = {}
        eng = Engagement.objects.get(id=eng_id)
        form = uploadReportForm()
        listReports = Report.objects.filter(engagement=eng)
        context['engagement'] = eng
        context['form'] = form
        context['list'] = listReports

        if request.method == 'POST':
                form = uploadReportForm(request.POST, request.FILES)
                
                if form.is_valid():
                    new_report = Report(engagement=eng, user=request.user, report_type=form.cleaned_data["report_type"], note=form.cleaned_data["note"], file=form.cleaned_data['file'])
                    new_report.save()
                    
                    # Handle vulnerability counts from the integrated form
                    for severity in ['critical', 'high', 'medium', 'low']:
                        # Create new vulnerabilities
                        new_count = form.cleaned_data.get(f'{severity}_new', 0)
                        for i in range(new_count):
                            Vulnerability.objects.create(
                                title=f"{severity.title()} Vulnerability {i+1}",
                                description=f"New {severity} vulnerability found in {new_report.report_type} report",
                                severity=severity.title(),
                                status='Open',
                                report=new_report,
                                engagement=eng,
                                created_by=request.user
                            )
                        
                        # Create fixed vulnerabilities
                        fixed_count = form.cleaned_data.get(f'{severity}_fixed', 0)
                        for i in range(fixed_count):
                            Vulnerability.objects.create(
                                title=f"Fixed {severity.title()} Vulnerability {i+1}",
                                description=f"Previously identified {severity} vulnerability now fixed",
                                severity=severity.title(),
                                status='Fixed',
                                report=new_report,
                                engagement=eng,
                                created_by=request.user
                            )
                    
                    thread = Thread(target = notifyNewReportUpload, args= (new_report, request))
                    thread.start()   
                    
                    context['reference']=new_report.reference
                    context['note'] = new_report.note
                    context['form'] = uploadReportForm()  # Reset form
                    return render(request,'CalendarinhoApp/UploadReports.html',context)
                else:
                    context['error'] = "Only .gpg files are allowed"
                    return render(request,'CalendarinhoApp/UploadReports.html',context)
        else:
            return render(request,'CalendarinhoApp/UploadReports.html',context)


@login_required
def downloadReport(request, refUUID=None):
    report = Report.objects.get(reference=refUUID)
    if(report != None): #Check if UUID is correct
        response = HttpResponse(report.file, content_type='application/pgp-encrypted')
        filename=report.file.name
        response['Content-Disposition'] = 'attachment; filename=%s' % (filename) #Filename
        return response
    else:
        return not_found(request)


@login_required
def deleteReport(request, refUUID=None):
    report = Report.objects.get(reference=refUUID)
    if(report != None): #Check if UUID is correct
        if(request.user.is_superuser or request.user==report.user):
            eng_id = report.engagement.id
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
                        'engagement_name': engagement.name,
                        'start_date': engagement.start_date,
                        'end_date': engagement.end_date,
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
                        'engagement_name': engagement.name,
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
    employees = engagement.employees.exclude(id=user.id)
    context = {
        'message': f'New comment on your engagement by {user.get_full_name()}.',
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.name,
        'user': user,
        'commentbody': comment.body,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }
    try:
        with mail.get_connection() as connection:
            for employee in employees :
                context = {
                        'first_name': employee.first_name,
                        'message': 'New comment on your engagement by ' + user.first_name + ' ' + user.last_name + '.',
                        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement',
                            args=[engagement.id])),
                        'engagement_name': engagement.name,
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
    engagement = report.engagement
    employees = engagement.employees.exclude(id=uploader.id)

    context = {
        'first_name': uploader.first_name,
        'message': f'New report uploaded on your engagement by {uploader.get_full_name()}.',
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.name,
        'reportType': report.reportType,
        'user': uploader,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }

    try:
        with mail.get_connection() as connection:
            for employee in employees:
                email_body = loader.render_to_string(
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
        'engagement_name': engagement.name,
        'user': user,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }

    try:
        with mail.get_connection() as connection:
            for manager in managers:
                context = {**base_context, 'first_name': manager.first_name}
                
                email_body = loader.render_to_string(
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
