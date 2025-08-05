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
    # Use optimized service function for better performance
    from .service import get_enhanced_engagement_data
    from .forms import AdvancedEngagementFilterForm
    
    # Initialize filter form
    filter_form = AdvancedEngagementFilterForm(request.GET or None)
    
    # Get enhanced engagement data with optimized queries
    data = get_enhanced_engagement_data()
    
    # If this is an AJAX request for filtered data, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from .api_filters import apply_engagement_filters, paginate_data
        
        filters = {}
        if filter_form.is_valid():
            filters = {k: v for k, v in filter_form.cleaned_data.items() if v is not None and v != ''}
        
        # Apply filters
        filtered_engagements = apply_engagement_filters(data['engagements'], filters)
        
        # Sort options
        sort_by = request.GET.get('sort_by', 'priority_score')
        sort_order = request.GET.get('sort_order', 'desc')
        
        if sort_by in ['name', 'clientName', 'startDate', 'endDate', 'priority_score', 'risk_score']:
            reverse_sort = sort_order == 'desc'
            filtered_engagements.sort(
                key=lambda x: x.get(sort_by, ''), 
                reverse=reverse_sort
            )
        
        # Pagination
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 25))
        
        paginated_data = paginate_data(filtered_engagements, page, per_page)
        
        return JsonResponse({
            'success': True,
            'engagements': paginated_data['data'],
            'pagination': paginated_data['pagination'],
            'summary': {
                'total_filtered': len(filtered_engagements),
                'total_unfiltered': len(data['engagements']),
                'engagement_stats': data['engagement_stats'],
                'filters_applied': len([k for k, v in filters.items() if v])
            }
        })
    
    context = {
        'table': data['engagements'],
        'engagement_stats': data['engagement_stats'],
        'filter_form': filter_form,
        'total_engagements': len(data['engagements'])
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
            new_comment.engagement = engagement
            # Assign the current user to the comment
            new_comment.user = request.user
            # Save the comment to the database
            new_comment.save()
            
            # Parse mentions from comment body
            mentioned_users, everyone_mentioned = parse_mentions_from_comment(
                new_comment.body, engagement
            )
            
            # Save mentioned users to the comment
            if mentioned_users:
                new_comment.mentioned_users.set(mentioned_users)
            
            # Handle notifications
            if mentioned_users:
                # Send mention notifications to mentioned users
                mention_thread = Thread(
                    target=notifyMentionedUsers, 
                    args=(new_comment, mentioned_users, everyone_mentioned, request)
                )
                mention_thread.start()
                
                # Send regular comment notifications to non-mentioned users (excluding comment author)
                mentioned_user_ids = [u.id for u in mentioned_users]
                regular_notification_users = engagement.employees.exclude(
                    id__in=mentioned_user_ids + [request.user.id]
                )
                
                if regular_notification_users.exists():
                    # Send regular notifications using a modified version of notifyNewComment
                    regular_thread = Thread(
                        target=notifyRegularCommentUsers, 
                        args=(new_comment, regular_notification_users, request)
                    )
                    regular_thread.start()
            else:
                # No mentions, send regular notification to all engagement users
                thread = Thread(target=notifyNewComment, args=(new_comment, request))
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
        return HttpResponseRedirect("/engagement/"+str(comment.engagement.id))
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
    engagement = comment.engagement
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


import re
from django.db.models import Q


@login_required
def api_search_users_for_mention(request, eng_id):
    """API endpoint for searching users to mention in comments"""
    try:
        engagement = Engagement.objects.get(id=eng_id)
        
        # Check if user has access to this engagement
        if not engagement.employees.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        query = request.GET.get('q', '').strip()
        
        # Get all users in the engagement, ordered consistently by first name
        engagement_users = engagement.employees.all().order_by('first_name', 'last_name', 'username')
        
        # Prepare user data for response
        users_data = []
        
        # Always add "Everyone" option at the top for empty queries or if query matches "everyone"
        include_everyone = not query or 'everyone' in query.lower()
        if include_everyone:
            users_data.append({
                'id': 'everyone',
                'username': 'everyone',
                'display_name': 'Everyone',
                'full_name': 'Everyone in this engagement',
                'is_special': True
            })
        
        # Filter and add individual users
        if query:
            # Search ALL active users (not just engagement members) when there's a query
            all_users = Employee.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query),
                is_active=True
            ).order_by('first_name', 'last_name', 'username')
            
            # Prioritize engagement users in results
            engagement_user_ids = set(engagement_users.values_list('id', flat=True))
            engagement_matches = [u for u in all_users if u.id in engagement_user_ids]
            other_matches = [u for u in all_users if u.id not in engagement_user_ids]
            
            # Combine results with engagement users first
            combined_users = engagement_matches + other_matches
            
            # Limit results, accounting for "Everyone" option if included
            limit = 9 if include_everyone else 10
            filtered_users = combined_users[:limit]
        else:
            # For empty query, return all users (up to limit)
            # Since "Everyone" is already included, limit to 9 users
            filtered_users = engagement_users[:9]
        
        # Add individual users to results
        for user in filtered_users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'display_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'full_name': user.get_full_name() or user.username,
                'is_special': False
            })
        
        return JsonResponse({
            'users': users_data,
            'count': len(users_data)
        })
        
    except Engagement.DoesNotExist:
        return JsonResponse({'error': 'Engagement not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in user search API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def parse_mentions_from_comment(comment_body, engagement):
    """
    Parse @mentions from comment body and return list of mentioned users
    Supports both @username and @"First Last" name formats
    """
    mentioned_users = []
    everyone_mentioned = False
    
    # Pattern 1: @"First Last" - names in quotes
    quoted_pattern = r'@"([^"]+)"'
    quoted_mentions = re.findall(quoted_pattern, comment_body, re.IGNORECASE)
    
    # Pattern 2: @word - single word mentions (usernames or "everyone")
    word_pattern = r'@(\w+)'
    word_mentions = re.findall(word_pattern, comment_body, re.IGNORECASE)
    
    # Process quoted name mentions (e.g., @"John Doe")
    for full_name in quoted_mentions:
        if full_name.lower() == 'everyone':
            everyone_mentioned = True
        else:
            # Try to find user by full name
            name_parts = full_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
                try:
                    # Search ALL users first
                    user = Employee.objects.get(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name,
                        is_active=True
                    )
                    mentioned_users.append(user)
                except Employee.DoesNotExist:
                    # Try partial matches in all users
                    potential_users = Employee.objects.filter(
                        Q(first_name__icontains=first_name) & Q(last_name__icontains=last_name),
                        is_active=True
                    )
                    if potential_users.exists():
                        mentioned_users.append(potential_users.first())
    
    # Process single word mentions (usernames or "everyone")
    for word in word_mentions:
        if word.lower() == 'everyone':
            everyone_mentioned = True
        else:
            # Try to find the user by username first, then by first name (search ALL users)
            try:
                user = Employee.objects.get(username__iexact=word, is_active=True)
                mentioned_users.append(user)
            except Employee.DoesNotExist:
                try:
                    user = Employee.objects.get(first_name__iexact=word, is_active=True)
                    mentioned_users.append(user)
                except Employee.DoesNotExist:
                    # User not found, skip
                    pass
    
    # If "everyone" was mentioned, add all engagement employees (but don't duplicate)
    if everyone_mentioned:
        all_engagement_users = list(engagement.employees.all())
        mentioned_users.extend(all_engagement_users)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_mentioned_users = []
    for user in mentioned_users:
        if user.id not in seen:
            seen.add(user.id)
            unique_mentioned_users.append(user)
    
    return unique_mentioned_users, everyone_mentioned


def notifyMentionedUsers(comment, mentioned_users, everyone_mentioned, request):
    """
    Send notifications to users mentioned in a comment
    """
    user = comment.user
    engagement = comment.engagement
    
    # Exclude the comment author from notifications
    users_to_notify = [u for u in mentioned_users if u.id != user.id]
    
    if not users_to_notify:
        return
    
    # Determine the notification message
    if everyone_mentioned:
        message_text = f'{user.get_full_name()} mentioned everyone in a comment on your engagement.'
    else:
        message_text = f'{user.get_full_name()} mentioned you in a comment on your engagement.'
    
    context = {
        'message': message_text,
        'engagement_url': request.build_absolute_uri(reverse('CalendarinhoApp:engagement', args=[engagement.id])),
        'engagement_name': engagement.name,
        'user': user,
        'commentbody': comment.body,
        'protocol': 'https' if settings.USE_HTTPS else 'http',
        'domain': settings.DOMAIN,
    }
    
    try:
        with mail.get_connection() as connection:
            for mentioned_user in users_to_notify:
                user_context = {
                    **context,
                    'first_name': mentioned_user.first_name,
                    'mentioned_user': mentioned_user,
                }
                
                email_body = loader.render_to_string(
                    'CalendarinhoApp/emails/mention_notification_email.html', 
                    user_context
                )
                
                subject = f'You were mentioned in a comment on {engagement.name}'
                if everyone_mentioned:
                    subject = f'Everyone was mentioned in a comment on {engagement.name}'
                
                email = EmailMessage(
                    subject,
                    email_body,
                    to=[mentioned_user.email],
                    connection=connection
                )
                email.content_subtype = "html"
                email.send()
                
    except ConnectionRefusedError as e:
        logger.error(f"Failed to send mention notification emails: {e}")


def notifyRegularCommentUsers(comment, users_to_notify, request):
    """
    Send regular comment notifications to specific users (used when some users are mentioned)
    """
    user = comment.user
    engagement = comment.engagement
    
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
            for employee in users_to_notify:
                user_context = {
                    **context,
                    'first_name': employee.first_name,
                }
                
                email_body = loader.render_to_string(
                    'CalendarinhoApp/emails/engagement_comment_email.html', 
                    user_context
                )
                
                email = EmailMessage(
                    'New comment on your engagement', 
                    email_body, 
                    to=[employee.email], 
                    connection=connection
                )
                email.content_subtype = "html"
                email.send()
                
    except ConnectionRefusedError as e:
        logger.error(f"Failed to send regular comment emails: {e}")
