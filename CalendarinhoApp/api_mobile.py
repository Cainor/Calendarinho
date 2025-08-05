"""
Mobile-Optimized API Module for Phase 2 Backend Features

This module provides mobile-optimized data structures and endpoints
specifically designed for mobile card layouts and touch interfaces.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
import math
from typing import Dict, List, Any

from .models import Engagement, Client, Vulnerability
from users.models import CustomUser as Employee


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text for mobile display"""
    if not text:
        return ""
    return text[:max_length] + "..." if len(text) > max_length else text


def get_priority_level(score: int) -> str:
    """Convert numeric score to priority level"""
    if score >= 15:
        return "high"
    elif score >= 5:
        return "medium"
    else:
        return "low"


def get_status_color(status: str) -> str:
    """Get color class for status"""
    colors = {
        'ongoing': 'success',
        'upcoming': 'info',
        'completed': 'secondary',
        'overdue': 'danger',
        'available': 'success',
        'engaged': 'warning',
        'vacation': 'info',
        'training': 'primary'
    }
    return colors.get(status.lower(), 'secondary')


@login_required
def api_mobile_dashboard(request):
    """Mobile-optimized dashboard data"""
    today = timezone.now().date()
    
    # Quick stats for dashboard cards
    stats = {
        'ongoing_engagements': Engagement.objects.filter(
            start_date__lte=today, end_date__gte=today
        ).count(),
        'open_vulnerabilities': Vulnerability.objects.filter(status='Open').count(),
        'critical_vulnerabilities': Vulnerability.objects.filter(
            status='Open', severity='Critical'
        ).count(),
        'available_employees': Employee.objects.filter(is_active=True).exclude(
            engagements__start_date__lte=today,
            engagements__end_date__gte=today
        ).count()
    }
    
    # Recent activity (limited for mobile)
    recent_vulnerabilities = Vulnerability.objects.select_related(
        'engagement__client'
    ).order_by('-created_at')[:5]
    
    recent_activity = []
    for vuln in recent_vulnerabilities:
        recent_activity.append({
            'id': vuln.id,
            'type': 'vulnerability',
            'title': truncate_text(vuln.title, 30),
            'subtitle': f"{vuln.severity} • {vuln.engagement.client.acronym}",
            'timestamp': vuln.created_at.isoformat(),
            'severity': vuln.severity.lower(),
            'color': vuln.get_severity_color()
        })
    
    # Urgent items requiring attention
    urgent_items = []
    
    # Engagements ending soon
    ending_soon = Engagement.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        end_date__lte=today + timezone.timedelta(days=7)
    ).select_related('client')[:3]
    
    for eng in ending_soon:
        days_left = (eng.end_date - today).days
        urgent_items.append({
            'id': eng.id,
            'type': 'engagement_ending',
            'title': truncate_text(eng.name, 25),
            'subtitle': f"Ends in {days_left} day{'s' if days_left != 1 else ''}",
            'client': eng.client.acronym,
            'color': 'warning',
            'priority': 'high' if days_left <= 3 else 'medium'
        })
    
    # Critical vulnerabilities
    critical_vulns = Vulnerability.objects.filter(
        status='Open', severity='Critical'
    ).select_related('engagement__client')[:3]
    
    for vuln in critical_vulns:
        days_old = (today - vuln.created_at.date()).days
        urgent_items.append({
            'id': vuln.id,
            'type': 'critical_vulnerability',
            'title': truncate_text(vuln.title, 25),
            'subtitle': f"Critical • {days_old} days old",
            'client': vuln.engagement.client.acronym,
            'color': 'danger',
            'priority': 'high'
        })
    
    # Sort urgent items by priority
    priority_order = {'high': 1, 'medium': 2, 'low': 3}
    urgent_items.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
    
    return JsonResponse({
        'success': True,
        'data': {
            'stats': stats,
            'recent_activity': recent_activity,
            'urgent_items': urgent_items[:10],  # Limit for mobile
            'last_updated': timezone.now().isoformat()
        }
    })


@login_required
def api_mobile_engagements(request):
    """Mobile-optimized engagements list"""
    page = int(request.GET.get('page', 1))
    per_page = 10  # Smaller pages for mobile
    status_filter = request.GET.get('status', 'all')
    
    today = timezone.now().date()
    queryset = Engagement.objects.select_related('client', 'service_type')
    
    # Apply status filter
    if status_filter == 'ongoing':
        queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
    elif status_filter == 'upcoming':
        queryset = queryset.filter(start_date__gt=today)
    elif status_filter == 'completed':
        queryset = queryset.filter(end_date__lt=today)
    
    # Pagination
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    # Format data for mobile cards
    engagement_cards = []
    for eng in page_obj:
        # Calculate status and progress
        if eng.start_date > today:
            status = "upcoming"
            progress = 0
            status_text = f"Starts {eng.start_date.strftime('%m/%d')}"
            color = "info"
        elif eng.start_date <= today <= eng.end_date:
            status = "ongoing"
            total_days = (eng.end_date - eng.start_date).days
            elapsed_days = (today - eng.start_date).days
            progress = int((elapsed_days / total_days) * 100) if total_days > 0 else 0
            remaining_days = (eng.end_date - today).days
            status_text = f"{remaining_days}d left"
            color = "warning" if remaining_days <= 7 else "success"
        else:
            status = "completed"
            progress = 100
            status_text = f"Done {eng.end_date.strftime('%m/%d')}"
            color = "secondary"
        
        # Get team info
        team_size = eng.employees.count()
        
        # Get vulnerability info
        open_vulns = eng.vulnerabilities.filter(status='Open').count()
        critical_vulns = eng.vulnerabilities.filter(
            status='Open', severity='Critical'
        ).count()
        
        # Calculate priority
        priority_score = 0
        if status == "ongoing":
            priority_score += 10
            if progress > 80:  # Near completion
                priority_score += 5
        elif status == "upcoming":
            days_until = (eng.start_date - today).days
            if days_until <= 14:
                priority_score += 3
        
        if critical_vulns > 0:
            priority_score += critical_vulns * 5
        elif open_vulns > 0:
            priority_score += open_vulns
        
        engagement_cards.append({
            'id': eng.id,
            'title': truncate_text(eng.name, 35),
            'subtitle': f"{eng.client.acronym} • {truncate_text(eng.service_type.name, 20)}",
            'status': status,
            'status_text': status_text,
            'color': color,
            'progress': progress,
            'team_size': team_size,
            'open_vulnerabilities': open_vulns,
            'critical_vulnerabilities': critical_vulns,
            'priority': get_priority_level(priority_score),
            'start_date': eng.start_date.isoformat(),
            'end_date': eng.end_date.isoformat(),
            'client_id': eng.client.id,
            'has_issues': critical_vulns > 0 or (status == 'ongoing' and progress > 90)
        })
    
    return JsonResponse({
        'success': True,
        'engagements': engagement_cards,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_items': paginator.count
        },
        'filters': {
            'current_status': status_filter,
            'available_statuses': [
                {'value': 'all', 'label': 'All'},
                {'value': 'ongoing', 'label': 'Ongoing'},
                {'value': 'upcoming', 'label': 'Upcoming'},
                {'value': 'completed', 'label': 'Completed'}
            ]
        }
    })


@login_required
def api_mobile_clients(request):
    """Mobile-optimized clients list"""
    page = int(request.GET.get('page', 1))
    per_page = 10
    activity_filter = request.GET.get('activity', 'all')
    
    today = timezone.now().date()
    # Simple mobile client list
    client_cards = []
    for client in Client.objects.all()[:per_page]:
        client_cards.append({
            'id': client.id,
            'name': client.name,
            'acronym': client.acronym,
            'code': client.code
        })
    
    return JsonResponse({
        'success': True,
        'clients': client_cards
    })


@login_required
def api_mobile_dashboard(request):
    """Mobile-optimized dashboard data"""
    today = timezone.now().date()
    
    data = {
        'stats': {
            'ongoing_engagements': Engagement.objects.filter(
                start_date__lte=today, end_date__gte=today
            ).count(),
            'available_employees': Employee.objects.filter(is_active=True).count(),
            'total_clients': Client.objects.count()
        },
        'recent_activity': [],
        'urgent_items': []
    }
    
    return JsonResponse({
        'success': True,
        'data': data
    })


@login_required
def api_mobile_engagements(request):
    """Mobile-optimized engagements list"""
    status_filter = request.GET.get('status', 'all')
    
    engagement_cards = []
    for eng in Engagement.objects.select_related('client')[:10]:
        engagement_cards.append({
            'id': eng.id,
            'name': eng.name,
            'client_name': eng.client.name,
            'start_date': eng.start_date.isoformat(),
            'end_date': eng.end_date.isoformat()
        })
    
    return JsonResponse({
        'success': True,
        'engagements': engagement_cards
    })


@login_required
def api_mobile_vulnerabilities(request):
    """Mobile-optimized vulnerabilities list"""
    return JsonResponse({
        'success': True,
        'vulnerabilities': []
    })


@login_required  
def api_mobile_employees(request):
    """Simple mobile employees list"""
    employee_cards = []
    for emp in Employee.objects.filter(is_active=True)[:10]:
        employee_cards.append({
            'id': emp.id,
            'name': emp.get_full_name(),
            'email': emp.email
        })
    
    return JsonResponse({
        'success': True,
        'employees': employee_cards
    })


@login_required
def api_mobile_quick_actions(request):
    """Simple mobile quick actions"""
    actions = [
        {
            'id': 'create_engagement',
            'title': 'New Engagement',
            'url': '/Engagement/add'
        }
    ]
    
    return JsonResponse({
        'success': True,
        'actions': actions
    })