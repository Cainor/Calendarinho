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
from django.utils import timezone
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
        
        # Order vulnerabilities by severity priority: Critical > High > Medium > Low
        severity_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
        ordered_vulnerabilities = sorted(
            eng.vulnerabilities.all(),
            key=lambda v: (severity_order.get(v.severity, 5), v.created_at)
        )
        
        context['engagement'] = eng
        context['form'] = form
        context['list'] = listReports
        context['ordered_vulnerabilities'] = ordered_vulnerabilities

        if request.method == 'POST':
                form = uploadReportForm(request.POST, request.FILES)
                
                if form.is_valid():
                    new_report = Report(engagement=eng, user=request.user, report_type=form.cleaned_data["report_type"], note=form.cleaned_data["note"], file=form.cleaned_data['file'])
                    new_report.save()
                    
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


@login_required
def toggleVulnerabilityStatus(request, vuln_id):
    """AJAX endpoint to toggle vulnerability status between Open and Fixed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        vulnerability = Vulnerability.objects.get(id=vuln_id)
        
        # Check permissions - only creators, superusers, or managers can modify
        if not (request.user == vulnerability.created_by or request.user.is_superuser or 
                request.user.user_type == 'M'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Toggle status
        if vulnerability.status == 'Open':
            vulnerability.status = 'Fixed'
            vulnerability.fixed_at = timezone.now()
            vulnerability.fixed_by = request.user
        else:
            vulnerability.status = 'Open'
            vulnerability.fixed_at = None
            vulnerability.fixed_by = None
        
        vulnerability.save()
        
        return JsonResponse({
            'success': True, 
            'status': vulnerability.status,
            'fixed_at': vulnerability.fixed_at.isoformat() if vulnerability.fixed_at else None,
            'fixed_by': str(vulnerability.fixed_by) if vulnerability.fixed_by else None
        })
        
    except Vulnerability.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vulnerability not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required 
def updateVulnerabilityTitle(request, vuln_id):
    """AJAX endpoint to update vulnerability title"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return JsonResponse({'success': False, 'error': 'Title cannot be empty'}, status=400)
        
        vulnerability = Vulnerability.objects.get(id=vuln_id)
        
        # Check permissions
        if not (request.user == vulnerability.created_by or request.user.is_superuser or 
                request.user.user_type == 'M'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        vulnerability.title = new_title
        vulnerability.save()
        
        return JsonResponse({'success': True, 'title': vulnerability.title})
        
    except Vulnerability.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vulnerability not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def deleteVulnerability(request, vuln_id):
    """AJAX endpoint to delete a vulnerability"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        vulnerability = Vulnerability.objects.get(id=vuln_id)
        
        # Check permissions - only creators, superusers, or managers can delete
        if not (request.user == vulnerability.created_by or request.user.is_superuser or 
                request.user.user_type == 'M'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        vulnerability.delete()
        
        return JsonResponse({'success': True})
        
    except Vulnerability.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vulnerability not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def addVulnerabilities(request, eng_id):
    """AJAX endpoint to add vulnerabilities to an engagement"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        eng = Engagement.objects.get(id=eng_id)
        
        # Check permissions - only engaged users, superusers, or managers can add vulnerabilities
        if not (request.user in eng.employees.all() or request.user.is_superuser or 
                request.user.user_type == 'M'):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        severity_mapping = {
            'critical': 'Critical',
            'high': 'High', 
            'medium': 'Medium',
            'low': 'Low'
        }
        
        severity_abbrev = {
            'Critical': 'c',
            'High': 'h',
            'Medium': 'm', 
            'Low': 'l'
        }
        
        # Get existing vulnerability counts per severity for this engagement
        existing_counts = {}
        for sev_key, sev_title in severity_mapping.items():
            existing_counts[sev_title] = eng.vulnerabilities.filter(severity=sev_title).count()
        
        created_titles = []  # Track created titles
        created_vulns = []
        
        for sev_key, sev_title in severity_mapping.items():
            # Create new vulnerabilities
            new_count = int(request.POST.get(f'{sev_key}_new', 0))
            abbrev = severity_abbrev[sev_title]
            
            for i in range(new_count):
                vuln_number = existing_counts[sev_title] + i + 1
                title = f"{abbrev}{vuln_number}"
                created_titles.append(title)
                
                vuln = Vulnerability.objects.create(
                    title=title,
                    description=f"New {sev_title.lower()} severity vulnerability",
                    severity=sev_title,
                    status='Open',
                    report=None,  # Not associated with a specific report
                    engagement=eng,
                    created_by=request.user
                )
                created_vulns.append({
                    'id': vuln.id,
                    'title': vuln.title,
                    'severity': vuln.severity,
                    'status': vuln.status
                })
                
            existing_counts[sev_title] += new_count
        
        return JsonResponse({
            'success': True, 
            'created_titles': ' '.join(created_titles),
            'vulnerabilities': created_vulns,
            'count': len(created_vulns)
        })
        
    except Engagement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Engagement not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
