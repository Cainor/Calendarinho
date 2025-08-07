from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Service, Client, Engagement
from .forms import ServiceForm
import logging
import datetime
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Prefetch
from users.models import CustomUser as Employee
from .models import Vulnerability

# Get an instance of a logger
logger = logging.getLogger(__name__)

@login_required
def ServiceCreate(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"status": True, "id": service.id, "name": service.name})
            return redirect('CalendarinhoApp:service', service_id=service.id)
    else:
        form = ServiceForm()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"status": False}, status=400)
    
    return render(request, 'CalendarinhoApp/Create_Service.html', {'form': form})

def get_optimized_employee_stats():
    """Get employee statistics with optimized queries"""
    today = timezone.now().date()
    
    # Get all employees with prefetched related data
    employees = Employee.objects.exclude(is_active=False).prefetch_related(
        Prefetch('engagements', queryset=Engagement.objects.filter(
            start_date__lte=today, end_date__gte=today
        )),
        'leave_set'
    )
    
    stats = {
        'total': employees.count(),
        'available': 0,
        'engaged': 0,
        'training': 0,
        'vacation': 0
    }
    
    for employee in employees:
        status = employee.currentStatus()[0]
        if status == 'Available':
            stats['available'] += 1
        elif status == 'Engaged':
            stats['engaged'] += 1
        elif status == 'Training':
            stats['training'] += 1
        elif status == 'Vacation':
            stats['vacation'] += 1
    
    return stats

def get_optimized_engagement_stats():
    """Get engagement statistics with optimized queries"""
    today = timezone.now().date()
    
    stats = Engagement.objects.aggregate(
        total=Count('id'),
        ongoing=Count('id', filter=Q(start_date__lte=today, end_date__gte=today)),
        upcoming=Count('id', filter=Q(start_date__gt=today)),
        completed=Count('id', filter=Q(end_date__lt=today))
    )
    
    return stats

def get_optimized_client_stats():
    """Get client statistics with optimized queries"""
    today = timezone.now().date()
    
    clients = Client.objects.annotate(
        current_eng_count=Count('engagements', filter=Q(
            engagements__start_date__lte=today,
            engagements__end_date__gte=today
        ))
    )
    
    stats = {
        'total': clients.count(),
        'active': clients.filter(current_eng_count__gt=0).count()
    }
    
    return stats

def calculate_team_utilization(days=30):
    """Calculate overall team utilization rate"""
    employees = Employee.objects.exclude(is_active=False)
    if not employees.exists():
        return 0
    
    total_utilization = 0
    employee_count = employees.count()
    
    for employee in employees:
        utilization = employee.get_utilization_rate(days)
        total_utilization += utilization
    
    return round(total_utilization / employee_count, 2) if employee_count > 0 else 0

def get_dashboard_summary():
    """Get comprehensive dashboard summary with optimized queries"""
    return {
        'employees': get_optimized_employee_stats(),
        'engagements': get_optimized_engagement_stats(),
        'clients': get_optimized_client_stats(),
        'utilization': calculate_team_utilization()
    }

def get_enhanced_employee_data():
    """Get enhanced employee data for table display with optimized queries"""
    today = timezone.now().date()
    
    # Get all employees with prefetched related data for efficiency
    employees = Employee.objects.exclude(is_active=False).prefetch_related(
        Prefetch('engagements', queryset=Engagement.objects.select_related('client', 'service_type')),
        'leave_set'
    )
    
    employee_data = []
    employee_counts = {
        'total': employees.count(),
        'available': 0,
        'engaged': 0,
        'training': 0,
        'vacation': 0
    }
    
    for emp in employees:
        # Get current status
        empstat = emp.currentStatus()
        status_type = empstat[0] if empstat else "Available"
        status_detail = empstat[1] if len(empstat) > 1 else ""
        
        # Count employee statuses for summary
        if status_type == "Available":
            employee_counts['available'] += 1
        elif status_type == "Engaged":
            employee_counts['engaged'] += 1
        elif status_type == "Training":
            employee_counts['training'] += 1
        elif status_type == "Vacation":
            employee_counts['vacation'] += 1
        
        # Calculate engagement statistics
        current_engagements = emp.engagements.filter(
            start_date__lte=today, end_date__gte=today
        ).count()
        
        upcoming_engagements = emp.engagements.filter(
            start_date__gt=today
        ).count()
        
        total_engagements = emp.engagements.count()
        
        # Get next event
        empnextev = emp.nextEvent()
        next_event = None
        start_date = None
        
        if empnextev and isinstance(empnextev, (tuple, list)) and len(empnextev) >= 2:
            event = empnextev[0]
            start_date = empnextev[1]
            
            if hasattr(event, 'leave_type'):
                leave = event
                if leave.leave_type == "Work from Home":
                    next_event = "Work from Home"
                else:
                    next_event = f"Leave: {leave.leave_type}"
                if hasattr(leave, 'note') and leave.note:
                    next_event += f" - {leave.note}"
            elif hasattr(event, 'name'):
                next_event = f"Engagement: {event.name}"
            elif isinstance(event, str):
                next_event = event
            elif event:
                next_event = str(event)
        else:
            next_event = "No upcoming event"
        
        # Calculate workload score based on current and upcoming engagements
        workload_score = (current_engagements * 2) + upcoming_engagements
        
        # Determine availability status with more granular information
        availability_status = "available"
        if status_type in ["Engaged", "Training", "Vacation"]:
            availability_status = "unavailable"
        elif upcoming_engagements > 0:
            availability_status = "partially_available"
        
        employee_info = {
            'id': emp.id,
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'full_name': emp.get_full_name(),
            'status_type': status_type,
            'status': f"{status_type}: {status_detail}" if status_detail else status_type,
            'end_date': empstat[2] if len(empstat) > 2 else None,
            'next_event': next_event,
            'start_date': start_date,
            'current_engagements': current_engagements,
            'upcoming_engagements': upcoming_engagements,
            'total_engagements': total_engagements,
            'utilization_rate': emp.get_utilization_rate(30),
            'workload_score': workload_score,
            'availability_status': availability_status,
            'user_type': emp.user_type,
            'is_manager': emp.user_type == 'M'
        }
        
        employee_data.append(employee_info)
    
    # Calculate overall utilization rate
    utilization_rate = round(
        (employee_counts['engaged'] / employee_counts['total']) * 100, 1
    ) if employee_counts['total'] > 0 else 0
    
    return {
        'employees': employee_data,
        'employee_counts': employee_counts,
        'utilization_rate': utilization_rate
    }

def get_enhanced_client_data():
    """Get enhanced client data for table display with optimized queries"""
    today = timezone.now().date()
    
    # Optimize query with prefetch_related to prevent N+1 queries
    clients = Client.objects.prefetch_related(
        'engagements__employees',
        'engagements__vulnerabilities'
    ).all()
    
    client_data = []
    client_stats = {
        'total': clients.count(),
        'active': 0,
        'inactive': 0
    }
    
    for cli in clients:
        # Calculate client activity metrics
        current_engagements = cli.count_current_engagements()
        total_engagements = cli.engagements.count()
        working_employees = cli.count_working_employees()
        
        # Calculate activity level
        if current_engagements > 0:
            activity_level = "high"
            client_stats['active'] += 1
        elif total_engagements > 0:
            # Check for recent engagements (within last 90 days)
            recent_engagements = cli.engagements.filter(
                end_date__gte=today - timezone.timedelta(days=90)
            ).count()
            if recent_engagements > 0:
                activity_level = "medium"
                client_stats['active'] += 1
            else:
                activity_level = "low"
                client_stats['inactive'] += 1
        else:
            activity_level = "low"
            client_stats['inactive'] += 1
        
        # Add vulnerability summary
        vuln_summary = cli.get_vulnerability_summary()
        
        # Calculate last engagement date and upcoming engagements
        last_engagement = cli.engagements.order_by('-end_date').first()
        upcoming_engagements = cli.engagements.filter(start_date__gt=today).count()
        
        # Calculate client risk score based on open vulnerabilities
        risk_score = (
            vuln_summary['critical_open'] * 10 +
            vuln_summary['high_open'] * 7 +
            vuln_summary.get('medium_open', 0) * 4 +
            vuln_summary.get('low_open', 0) * 1
        )
        
        # Calculate engagement history summary
        history_summary = cli.get_engagement_history_summary()
        
        # Calculate days since last engagement
        days_since_last = None
        if last_engagement and last_engagement.end_date:
            days_since_last = (today - last_engagement.end_date).days
        
        client_info = {
            'cliID': cli.id,
            'name': cli.name,
            'acronym': cli.acronym,
            'code': cli.code,
            'activity_level': activity_level,
            'current_engagements': current_engagements,
            'total_engagements': total_engagements,
            'working_employees': working_employees,
            'upcoming_engagements': upcoming_engagements,
            'last_engagement_date': last_engagement.end_date if last_engagement else None,
            'days_since_last_engagement': days_since_last,
            'activity_score': cli.get_activity_score(),
            'risk_score': risk_score,
            'history_summary': history_summary,
            'vulnerabilities': {
                'total_open': vuln_summary['total_open'],
                'total_fixed': vuln_summary['total_fixed'],
                'critical_open': vuln_summary['critical_open'],
                'high_open': vuln_summary['high_open'],
                'medium_open': vuln_summary.get('medium_open', 0),
                'low_open': vuln_summary.get('low_open', 0),
                'engagements_with_vulnerabilities': vuln_summary['engagements_with_vulnerabilities']
            }
        }
        
        client_data.append(client_info)
    
    # Sort by activity level and name
    activity_order = {'high': 1, 'medium': 2, 'low': 3}
    client_data.sort(key=lambda x: (activity_order.get(x['activity_level'], 4), x['name']))
    
    return {
        'clients': client_data,
        'client_stats': client_stats
    }

def get_enhanced_engagement_data():
    """Get enhanced engagement data for table display with optimized queries"""
    today = timezone.now().date()
    
    # Optimize query with select_related and prefetch_related to prevent N+1 queries
    engagements = Engagement.objects.select_related(
        'client', 'service_type', 'project_manager'
    ).prefetch_related(
        'employees', 'vulnerabilities'
    ).all()
    
    engagement_data = []
    engagement_stats = {
        'total': engagements.count(),
        'ongoing': 0,
        'future': 0,
        'completed': 0
    }
    
    for eng in engagements:
        # Calculate engagement status and duration
        if eng.start_date > today:
            status = "future"
            engagement_stats['future'] += 1
            days_until_start = (eng.start_date - today).days
            status_detail = f"Starts in {days_until_start} days"
            progress_percentage = 0
        elif eng.start_date <= today <= eng.end_date:
            status = "ongoing"
            engagement_stats['ongoing'] += 1
            days_remaining = (eng.end_date - today).days
            progress_percentage = eng.days_left_percentage()
            if days_remaining == 0:
                status_detail = "Ends today"
            elif days_remaining == 1:
                status_detail = "Ends tomorrow"
            else:
                status_detail = f"{days_remaining} days remaining"
        else:
            status = "completed"
            engagement_stats['completed'] += 1
            days_since_completion = (today - eng.end_date).days
            status_detail = f"Completed {days_since_completion} days ago"
            progress_percentage = 100
        
        # Calculate total duration
        total_days = (eng.end_date - eng.start_date).days + 1
        
        # Get employee count and team utilization
        employee_count = eng.employees.count()
        team_utilization = eng.get_team_utilization()
        
        # Add vulnerability summary
        vuln_summary = eng.get_vulnerability_summary()
        
        # Calculate risk score and remediation rate
        risk_score = eng.get_vulnerability_risk_score()
        remediation_rate = eng.get_vulnerability_remediation_rate()
        
        # Get project manager info
        project_manager_name = eng.project_manager.name if eng.project_manager else None
        
        # Calculate priority score based on status, risk, and timeline
        priority_score = 0
        if status == "ongoing":
            priority_score += 10
            if days_remaining <= 7:  # Ending soon
                priority_score += 5
        elif status == "future" and days_until_start <= 14:  # Starting soon
            priority_score += 3
        
        # Add risk factor to priority
        if risk_score > 50:
            priority_score += 5
        elif risk_score > 20:
            priority_score += 2
        
        engagement_info = {
            'engID': eng.id,
            'name': eng.name,
            'clientName': eng.client.name,
            'clientID': eng.client.id,
            'serviceType': eng.service_type.name,
            'startDate': eng.start_date,
            'endDate': eng.end_date,
            'status': status,
            'status_detail': status_detail,
            'progress_percentage': progress_percentage,
            'duration_days': total_days,
            'employee_count': employee_count,
            'team_utilization': team_utilization,
            'risk_score': risk_score,
            'remediation_rate': remediation_rate,
            'priority_score': priority_score,
            'project_manager': project_manager_name,
            'scope_line_count': len(eng.scope.split('\n')) if eng.scope else 0,
            'vulnerabilities': {
                'total_open': vuln_summary['total_open'],
                'total_fixed': vuln_summary['total_fixed'],
                'critical_open': vuln_summary['critical_open'],
                'high_open': vuln_summary['high_open'],
                'medium_open': vuln_summary.get('medium_open', 0),
                'low_open': vuln_summary.get('low_open', 0)
            }
        }
        
        engagement_data.append(engagement_info)
    
    # Sort by priority score (highest first), then by start date (most recent first)
    engagement_data.sort(key=lambda x: (x['priority_score'], x['startDate']), reverse=True)
    
    return {
        'engagements': engagement_data,
        'engagement_stats': engagement_stats
    }

def get_employee_availability_matrix(start_date=None, end_date=None):
    """Get employee availability matrix for a date range"""
    if not start_date:
        start_date = timezone.now().date()
    if not end_date:
        end_date = start_date + timezone.timedelta(days=30)
    
    employees = Employee.objects.exclude(is_active=False)
    availability_matrix = []
    
    for emp in employees:
        availability_info = {
            'employee_id': emp.id,
            'employee_name': emp.get_full_name(),
            'availability_periods': [],
            'conflict_periods': []
        }
        
        # Check each day in the range
        current_date = start_date
        while current_date <= end_date:
            has_conflict = emp.overlapCheck(current_date, current_date)
            
            if has_conflict:
                # Find what's causing the conflict
                status = emp.currentStatus() if current_date == timezone.now().date() else None
                conflict_info = {
                    'date': current_date,
                    'type': status[0] if status else 'Unknown',
                    'detail': status[1] if status and len(status) > 1 else ''
                }
                availability_info['conflict_periods'].append(conflict_info)
            else:
                availability_info['availability_periods'].append(current_date)
            
            current_date += timezone.timedelta(days=1)
        
        availability_matrix.append(availability_info)
    
    return availability_matrix

def get_workload_distribution():
    """Get workload distribution across employees"""
    today = timezone.now().date()
    employees = Employee.objects.exclude(is_active=False)
    
    workload_data = []
    total_workload = 0
    
    for emp in employees:
        current_engagements = emp.engagements.filter(
            start_date__lte=today, end_date__gte=today
        ).count()
        
        upcoming_engagements = emp.engagements.filter(
            start_date__gt=today,
            start_date__lte=today + timezone.timedelta(days=90)
        ).count()
        
        workload_score = (current_engagements * 2) + upcoming_engagements
        total_workload += workload_score
        
        workload_info = {
            'employee_id': emp.id,
            'employee_name': emp.get_full_name(),
            'current_engagements': current_engagements,
            'upcoming_engagements': upcoming_engagements,
            'workload_score': workload_score,
            'utilization_rate': emp.get_utilization_rate(30)
        }
        
        workload_data.append(workload_info)
    
    # Calculate workload percentages
    for workload_info in workload_data:
        workload_info['workload_percentage'] = round(
            (workload_info['workload_score'] / total_workload * 100), 2
        ) if total_workload > 0 else 0
    
    # Sort by workload score (highest first)
    workload_data.sort(key=lambda x: x['workload_score'], reverse=True)
    
    return workload_data

def get_client_risk_assessment():
    """Get client risk assessment based on vulnerabilities and engagement activity"""
    clients = Client.objects.prefetch_related('engagements__vulnerabilities').all()
    risk_assessments = []
    
    for client in clients:
        vuln_summary = client.get_vulnerability_summary()
        
        # Calculate risk score
        risk_score = (
            vuln_summary['critical_open'] * 10 +
            vuln_summary['high_open'] * 7 +
            vuln_summary.get('medium_open', 0) * 4 +
            vuln_summary.get('low_open', 0) * 1
        )
        
        # Calculate risk level
        if risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 20:
            risk_level = 'medium'
        elif risk_score > 0:
            risk_level = 'low'
        else:
            risk_level = 'none'
        
        # Calculate engagement frequency (engagements per year)
        total_engagements = client.engagements.count()
        first_engagement = client.engagements.order_by('start_date').first()
        
        engagement_frequency = 0
        if first_engagement and total_engagements > 0:
            days_since_first = (timezone.now().date() - first_engagement.start_date).days
            years_active = max(days_since_first / 365.25, 1)  # At least 1 year
            engagement_frequency = round(total_engagements / years_active, 2)
        
        risk_assessment = {
            'client_id': client.id,
            'client_name': client.name,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'vulnerabilities': vuln_summary,
            'engagement_frequency': engagement_frequency,
            'current_engagements': client.count_current_engagements(),
            'total_engagements': total_engagements,
            'remediation_priority': risk_score * (1 + client.count_current_engagements())
        }
        
        risk_assessments.append(risk_assessment)
    
    # Sort by remediation priority (highest first)
    risk_assessments.sort(key=lambda x: x['remediation_priority'], reverse=True)
    
    return risk_assessments

def get_engagement_timeline_conflicts(days_ahead=90):
    """Identify potential timeline conflicts for upcoming engagements"""
    today = timezone.now().date()
    future_date = today + timezone.timedelta(days=days_ahead)
    
    upcoming_engagements = Engagement.objects.filter(
        start_date__gte=today,
        start_date__lte=future_date
    ).select_related('client', 'service_type').prefetch_related('employees')
    
    conflicts = []
    
    for engagement in upcoming_engagements:
        conflict_info = {
            'engagement_id': engagement.id,
            'engagement_name': engagement.name,
            'client_name': engagement.client.name,
            'start_date': engagement.start_date,
            'end_date': engagement.end_date,
            'employee_conflicts': [],
            'resource_warnings': []
        }
        
        # Check for employee conflicts
        for employee in engagement.employees.all():
            if employee.overlapCheck(engagement.start_date, engagement.end_date):
                conflict_info['employee_conflicts'].append({
                    'employee_name': employee.get_full_name(),
                    'employee_id': employee.id
                })
        
        # Check for resource warnings (too many concurrent engagements)
        concurrent_engagements = Engagement.objects.filter(
            start_date__lte=engagement.end_date,
            end_date__gte=engagement.start_date
        ).exclude(id=engagement.id).count()
        
        if concurrent_engagements >= 5:  # Threshold for resource warning
            conflict_info['resource_warnings'].append(
                f"{concurrent_engagements} concurrent engagements during this period"
            )
        
        # Only include engagements with conflicts or warnings
        if conflict_info['employee_conflicts'] or conflict_info['resource_warnings']:
            conflicts.append(conflict_info)
    
    return conflicts

@login_required
def api_employee_stats(request):
    """API endpoint for employee statistics"""
    data = get_enhanced_employee_data()
    return JsonResponse({
        'success': True,
        'data': {
            'employees': data['employees'],
            'counts': data['employee_counts'],
            'utilization_rate': data['utilization_rate']
        }
    })

@login_required
def api_client_stats(request):
    """API endpoint for client statistics"""
    data = get_enhanced_client_data()
    return JsonResponse({
        'success': True,
        'data': {
            'clients': data['clients'],
            'stats': data['client_stats']
        }
    })

@login_required
def api_engagement_stats(request):
    """API endpoint for engagement statistics"""
    data = get_enhanced_engagement_data()
    return JsonResponse({
        'success': True,
        'data': {
            'engagements': data['engagements'],
            'stats': data['engagement_stats']
        }
    })

@login_required
def api_workload_distribution(request):
    """API endpoint for workload distribution"""
    data = get_workload_distribution()
    return JsonResponse({
        'success': True,
        'data': data
    })

@login_required
def api_availability_matrix(request):
    """API endpoint for employee availability matrix"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
    
    data = get_employee_availability_matrix(start_date, end_date)
    return JsonResponse({
        'success': True,
        'data': data
    })

@login_required
def api_client_risk_assessment(request):
    """API endpoint for client risk assessment"""
    data = get_client_risk_assessment()
    return JsonResponse({
        'success': True,
        'data': data
    })

@login_required
def api_timeline_conflicts(request):
    """API endpoint for engagement timeline conflicts"""
    days_ahead = request.GET.get('days_ahead', 90)
    try:
        days_ahead = int(days_ahead)
    except (ValueError, TypeError):
        days_ahead = 90
    
    data = get_engagement_timeline_conflicts(days_ahead)
    return JsonResponse({
        'success': True,
        'data': data
    })

@login_required
def api_dashboard_summary(request):
    """API endpoint for dashboard summary"""
    data = get_dashboard_summary()
    return JsonResponse({
        'success': True,
        'data': data
    })


def get_vulnerability_analytics():
    """Get comprehensive vulnerability analytics across all engagements"""
    today = timezone.now().date()
    
    # Get all vulnerabilities with related data
    vulnerabilities = Vulnerability.objects.select_related(
        'engagement__client', 'created_by', 'fixed_by'
    ).all()
    
    analytics = {
        'total_count': vulnerabilities.count(),
        'severity_breakdown': {},
        'status_breakdown': {},
        'overdue_count': 0,
        'recently_fixed': 0,
        'average_time_to_fix': 0,
        'top_vulnerable_clients': [],
        'engagement_risk_distribution': {},
        'monthly_trend': []
    }
    
    # Calculate severity and status breakdowns
    for severity in ['Critical', 'High', 'Medium', 'Low']:
        analytics['severity_breakdown'][severity] = {
            'open': vulnerabilities.filter(severity=severity, status='Open').count(),
            'fixed': vulnerabilities.filter(severity=severity, status='Fixed').count()
        }
    
    analytics['status_breakdown'] = {
        'open': vulnerabilities.filter(status='Open').count(),
        'fixed': vulnerabilities.filter(status='Fixed').count()
    }
    
    # Calculate overdue vulnerabilities
    severity_sla = {
        'Critical': 7,
        'High': 30,
        'Medium': 90,
        'Low': 180
    }
    
    overdue_count = 0
    for severity, days in severity_sla.items():
        cutoff_date = today - timezone.timedelta(days=days)
        overdue_count += vulnerabilities.filter(
            severity=severity,
            status='Open',
            created_at__date__lte=cutoff_date
        ).count()
    
    analytics['overdue_count'] = overdue_count
    
    # Recently fixed (last 30 days)
    recent_fixed_date = today - timezone.timedelta(days=30)
    analytics['recently_fixed'] = vulnerabilities.filter(
        status='Fixed',
        fixed_at__date__gte=recent_fixed_date
    ).count()
    
    # Average time to fix
    fixed_vulns = vulnerabilities.filter(status='Fixed', fixed_at__isnull=False)
    if fixed_vulns.exists():
        total_days = sum(
            (vuln.fixed_at.date() - vuln.created_at.date()).days 
            for vuln in fixed_vulns
        )
        analytics['average_time_to_fix'] = round(total_days / fixed_vulns.count(), 1)
    
    # Top vulnerable clients
    from django.db.models import Count
    client_vuln_counts = Client.objects.annotate(
        open_vuln_count=Count('engagements__vulnerabilities', 
                            filter=Q(engagements__vulnerabilities__status='Open'))
    ).filter(open_vuln_count__gt=0).order_by('-open_vuln_count')[:5]
    
    analytics['top_vulnerable_clients'] = [
        {
            'client_name': client.name,
            'open_vulnerabilities': client.open_vuln_count,
            'client_id': client.id
        }
        for client in client_vuln_counts
    ]
    
    # Engagement risk distribution
    engagements_with_vulns = Engagement.objects.prefetch_related('vulnerabilities').all()
    risk_distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
    
    for eng in engagements_with_vulns:
        risk_score = eng.get_vulnerability_risk_score()
        if risk_score == 0:
            continue
        elif risk_score <= 10:
            risk_distribution['low'] += 1
        elif risk_score <= 30:
            risk_distribution['medium'] += 1
        elif risk_score <= 70:
            risk_distribution['high'] += 1
        else:
            risk_distribution['critical'] += 1
    
    analytics['engagement_risk_distribution'] = risk_distribution
    
    return analytics


def get_performance_metrics():
    """Get system performance metrics for monitoring"""
    today = timezone.now().date()
    
    # Calculate key performance indicators
    total_engagements = Engagement.objects.count()
    ongoing_engagements = Engagement.objects.filter(
        start_date__lte=today, end_date__gte=today
    ).count()
    
    # Team utilization over time
    employees = Employee.objects.exclude(is_active=False)
    total_employees = employees.count()
    engaged_employees = 0
    
    for emp in employees:
        if emp.engagements.filter(start_date__lte=today, end_date__gte=today).exists():
            engaged_employees += 1
    
    utilization_rate = round((engaged_employees / total_employees * 100), 2) if total_employees > 0 else 0
    
    # Client satisfaction metrics (based on vulnerability resolution)
    clients_with_open_vulns = Client.objects.filter(
        engagements__vulnerabilities__status='Open'
    ).distinct().count()
    
    total_active_clients = Client.objects.filter(
        engagements__start_date__lte=today,
        engagements__end_date__gte=today
    ).distinct().count()
    
    client_satisfaction_score = 100
    if total_active_clients > 0:
        client_satisfaction_score = round(
            ((total_active_clients - clients_with_open_vulns) / total_active_clients) * 100, 2
        )
    
    # Engagement completion rate (last 90 days)
    start_period = today - timezone.timedelta(days=90)
    completed_engagements = Engagement.objects.filter(
        end_date__gte=start_period,
        end_date__lt=today
    ).count()
    
    scheduled_engagements = Engagement.objects.filter(
        start_date__gte=start_period,
        start_date__lt=today
    ).count()
    
    completion_rate = 100
    if scheduled_engagements > 0:
        completion_rate = round((completed_engagements / scheduled_engagements) * 100, 2)
    
    return {
        'utilization_rate': utilization_rate,
        'engaged_employees': engaged_employees,
        'total_employees': total_employees,
        'client_satisfaction_score': client_satisfaction_score,
        'completion_rate': completion_rate,
        'ongoing_engagements': ongoing_engagements,
        'total_engagements': total_engagements,
        'clients_with_issues': clients_with_open_vulns,
        'total_active_clients': total_active_clients
    }


@login_required
def api_vulnerability_analytics(request):
    """API endpoint for vulnerability analytics"""
    data = get_vulnerability_analytics()
    return JsonResponse({
        'success': True,
        'data': data
    })


@login_required
def api_performance_metrics(request):
    """API endpoint for performance metrics"""
    data = get_performance_metrics()
    return JsonResponse({
        'success': True,
        'data': data
    })


@login_required
def api_enhanced_manager_dashboard(request):
    """API endpoint for enhanced manager dashboard data"""
    # Get date parameters from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - datetime.timedelta(days=90)
        
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD.'
        }, status=400)
    
    # Get enhanced dashboard data
    data = get_enhanced_manager_dashboard_data(start_date, end_date)
    
    # Convert employee objects to serializable format
    if data.get('enhanced_emp_data'):
        serializable_emp_data = []
        for emp_data in data['enhanced_emp_data']:
            if len(emp_data) >= 4:  # Enhanced format with utilization
                serializable_emp_data.append({
                    'employee_id': emp_data[0].id,
                    'employee_name': emp_data[0].get_full_name(),
                    'engaged_days': emp_data[1],
                    'utilization_rate': emp_data[2],
                    'utilization_status': emp_data[3]
                })
            else:  # Legacy format
                serializable_emp_data.append({
                    'employee_id': emp_data[0].id,
                    'employee_name': emp_data[0].get_full_name(),
                    'engaged_days': emp_data[1],
                    'utilization_rate': 0,
                    'utilization_status': 'unknown'
                })
        data['enhanced_emp_data'] = serializable_emp_data
    
    return JsonResponse({
        'success': True,
        'data': data,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    })


@login_required 
def api_team_utilization_breakdown(request):
    """API endpoint for detailed team utilization breakdown"""
    # Get date parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - datetime.timedelta(days=90)
        
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD.'
        }, status=400)
    
    # Get detailed utilization data
    utilization_data = calculate_enhanced_team_utilization(start_date, end_date)
    
    # Serialize employee data
    serializable_employees = []
    for emp_data in utilization_data['employee_details']:
        serializable_employees.append({
            'employee_id': emp_data['employee'].id,
            'employee_name': emp_data['employee'].get_full_name(),
            'engaged_days': emp_data['engaged_days'],
            'working_days': emp_data['working_days'],
            'utilization_rate': emp_data['utilization_rate'],
            'status': emp_data['status'],
            'user_type': emp_data['employee'].user_type
        })
    
    return JsonResponse({
        'success': True,
        'data': {
            'team_utilization': utilization_data['team_utilization'],
            'available_capacity': utilization_data['available_capacity'],
            'utilization_distribution': utilization_data['utilization_distribution'],
            'employee_details': serializable_employees,
            'underutilized_count': len(utilization_data['underutilized_employees']),
            'overutilized_count': len(utilization_data['overutilized_employees'])
        },
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    })


def get_search_suggestions(query: str, search_type: str = 'all'):
    """Get search suggestions for autocomplete functionality"""
    suggestions = []
    query = query.lower().strip()
    
    if not query or len(query) < 2:
        return suggestions
    
    if search_type in ['all', 'clients']:
        # Client suggestions
        clients = Client.objects.filter(
            Q(name__icontains=query) | Q(acronym__icontains=query)
        )[:5]
        
        for client in clients:
            suggestions.append({
                'type': 'client',
                'id': client.id,
                'label': client.name,
                'subtitle': client.acronym,
                'url': f'/client/{client.id}/'
            })
    
    if search_type in ['all', 'engagements']:
        # Engagement suggestions
        engagements = Engagement.objects.select_related('client').filter(
            Q(name__icontains=query) | Q(client__name__icontains=query)
        )[:5]
        
        for eng in engagements:
            suggestions.append({
                'type': 'engagement',
                'id': eng.id,
                'label': eng.name,
                'subtitle': f'{eng.client.name} • {eng.service_type.name}',
                'url': f'/engagement/{eng.id}/'
            })
    
    if search_type in ['all', 'employees']:
        # Employee suggestions
        employees = Employee.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query),
            is_active=True
        )[:5]
        
        for emp in employees:
            suggestions.append({
                'type': 'employee',
                'id': emp.id,
                'label': emp.get_full_name(),
                'subtitle': emp.user_type_display if hasattr(emp, 'user_type_display') else 'Employee',
                'url': f'/profile/{emp.id}/'
            })
    
    if search_type in ['all', 'vulnerabilities']:
        # Vulnerability suggestions
        vulnerabilities = Vulnerability.objects.select_related('engagement').filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:5]
        
        for vuln in vulnerabilities:
            suggestions.append({
                'type': 'vulnerability',
                'id': vuln.id,
                'label': vuln.title,
                'subtitle': f'{vuln.severity} • {vuln.engagement.name}',
                'url': f'/engagement/{vuln.engagement.id}/Reports/'
            })
    
    return suggestions[:10]  # Limit total suggestions


@login_required
def api_search_suggestions(request):
    """API endpoint for search suggestions"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')
    
    suggestions = get_search_suggestions(query, search_type)
    
    return JsonResponse({
        'success': True,
        'suggestions': suggestions,
        'query': query
    })


# Enhanced Manager Dashboard Functions

# Simple cache for expensive calculations (5 minute TTL)
_dashboard_cache = {}
CACHE_TTL = 300  # 5 minutes

def _get_cache_key(start_date, end_date, cache_type):
    """Generate cache key for dashboard calculations"""
    return f"{cache_type}_{start_date}_{end_date}"

def _is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    return (timezone.now().timestamp() - cache_entry.get('timestamp', 0)) < CACHE_TTL

def _set_cache(key, data):
    """Set cache entry with timestamp"""
    _dashboard_cache[key] = {
        'data': data,
        'timestamp': timezone.now().timestamp()
    }

def _get_cache(key):
    """Get cache entry if valid"""
    cache_entry = _dashboard_cache.get(key)
    if _is_cache_valid(cache_entry):
        return cache_entry['data']
    return None

def calculate_enhanced_team_utilization(start_date, end_date):
    """
    Calculate enhanced team utilization metrics with categorization
    Returns detailed utilization breakdown and identifies under/over utilized employees
    """
    # Check cache first
    cache_key = _get_cache_key(start_date, end_date, 'utilization')
    cached_result = _get_cache(cache_key)
    if cached_result:
        return cached_result
    
    employees = Employee.objects.exclude(is_active=False).prefetch_related(
        'engagements', 'leave_set'
    )
    
    if not employees.exists():
        return {
            'team_utilization': 0,
            'available_capacity': 100,
            'underutilized_employees': [],
            'overutilized_employees': [],
            'utilization_distribution': {'optimal': 0, 'under': 0, 'over': 0}
        }
    
    utilization_data = []
    total_utilization = 0
    
    for emp in employees:
        engaged_days = emp.countEngDays(start_date, end_date)
        
        # Calculate weekdays only using proper business day calculation
        import numpy as np
        from django.conf import settings
        working_days = np.busday_count(
            start_date, 
            end_date + timezone.timedelta(days=1),
            weekmask=settings.WORKING_DAYS
        )
        
        # Calculate utilization rate - this shows percentage of business days spent on client engagements
        # Note: 100% would mean working on engagements every single business day (unrealistic)
        # Typically 70-80% is considered high utilization in consulting
        raw_utilization = round((engaged_days / working_days) * 100, 2) if working_days > 0 else 0
        
        # For better business interpretation, we can scale the utilization
        # so that 70% engagement becomes 100% utilization target
        # utilization_rate = min(100, round((engaged_days / (working_days * 0.7)) * 100, 2)) if working_days > 0 else 0
        
        # For now, keep raw calculation but with better thresholds
        utilization_rate = raw_utilization
        
        emp_data = {
            'employee': emp,
            'engaged_days': engaged_days,
            'working_days': working_days,
            'utilization_rate': utilization_rate,
            'status': 'optimal'  # Default
        }
        
        # Categorize utilization (30-80% is optimal for realistic business scenarios)
        if utilization_rate < 30:
            emp_data['status'] = 'under'
        elif utilization_rate > 80:
            emp_data['status'] = 'over'
        
        utilization_data.append(emp_data)
        total_utilization += utilization_rate
    
    # Calculate team averages
    team_utilization = round(total_utilization / len(utilization_data), 2)
    available_capacity = max(0, round(100 - team_utilization, 2))
    
    # Categorize employees
    underutilized = [emp for emp in utilization_data if emp['status'] == 'under']
    overutilized = [emp for emp in utilization_data if emp['status'] == 'over']
    optimal = [emp for emp in utilization_data if emp['status'] == 'optimal']
    
    result = {
        'team_utilization': team_utilization,
        'available_capacity': available_capacity,
        'underutilized_employees': underutilized,
        'overutilized_employees': overutilized,
        'utilization_distribution': {
            'optimal': len(optimal),
            'under': len(underutilized),
            'over': len(overutilized)
        },
        'employee_details': utilization_data
    }
    
    # Cache the result
    _set_cache(cache_key, result)
    return result


def calculate_financial_intelligence(start_date, end_date):
    """
    Calculate financial intelligence metrics including revenue, costs, and variance
    """
    from django.conf import settings
    
    employees = Employee.objects.exclude(is_active=False)
    
    # Calculate total engaged days and costs
    total_engaged_days = 0
    total_cost = 0
    employee_costs = []
    
    for emp in employees:
        engaged_days = emp.countEngDays(start_date, end_date)
        emp_cost = engaged_days * settings.COST_PER_DAY
        
        total_engaged_days += engaged_days
        total_cost += emp_cost
        
        if engaged_days > 0:
            employee_costs.append({
                'employee': emp,
                'engaged_days': engaged_days,
                'cost': emp_cost
            })
    
    # Calculate average cost per employee per day
    active_employees = len([emp for emp in employee_costs if emp['engaged_days'] > 0])
    cost_per_emp_per_day = settings.COST_PER_DAY
    
    # Calculate monthly revenue run-rate (extrapolate from current period)
    period_days = (end_date - start_date).days + 1
    monthly_revenue = round((total_cost * 30) / period_days) if period_days > 0 else 0
    
    # Calculate budget variance without recursive call for performance
    # This is a simplified calculation - enhance with actual budget data when available
    expected_utilization = 75  # Target utilization percentage
    
    # Calculate actual utilization directly to avoid recursion
    total_utilization = 0
    employee_count = 0
    
    for emp_cost_data in employee_costs:
        if emp_cost_data['engaged_days'] > 0:
            emp = emp_cost_data['employee']
            # Calculate weekdays only
            import numpy as np
            from django.conf import settings
            working_days = np.busday_count(
                start_date, 
                end_date + timezone.timedelta(days=1),
                weekmask=settings.WORKING_DAYS
            )
            
            if working_days > 0:
                emp_utilization = round((emp_cost_data['engaged_days'] / working_days) * 100, 2)
                total_utilization += emp_utilization
                employee_count += 1
    
    actual_utilization = round(total_utilization / employee_count, 2) if employee_count > 0 else 0
    budget_variance = round(((actual_utilization - expected_utilization) / expected_utilization) * 100, 2) if expected_utilization > 0 else 0
    
    return {
        'monthly_revenue': monthly_revenue,
        'total_cost': total_cost,
        'cost_per_emp_per_day': cost_per_emp_per_day,
        'budget_variance': budget_variance,
        'total_engaged_days': total_engaged_days,
        'active_employees': active_employees,
        'employee_costs': employee_costs[:10]  # Top 10 for performance
    }


def calculate_client_health_scores():
    """
    Calculate client health scores based on engagement activity and vulnerability status
    Returns health scores and identifies clients needing attention
    """
    # Check cache first
    today = timezone.now().date()
    cache_key = f"client_health_{today}"
    cached_result = _get_cache(cache_key)
    if cached_result:
        return cached_result
    
    clients = Client.objects.prefetch_related(
        'engagements__vulnerabilities'
    ).all()
    
    client_health_data = []
    total_score = 0
    inactive_clients = []
    
    for client in clients:
        score_components = {
            'engagement_activity': 0,
            'vulnerability_status': 0,
            'communication': 0,
            'relationship_age': 0
        }
        
        # 1. Engagement Activity Score (0-40 points)
        current_engagements = client.count_current_engagements()
        recent_engagements = client.engagements.filter(
            end_date__gte=today - timezone.timedelta(days=90)
        ).count()
        
        score_components['engagement_activity'] = min(40, (current_engagements * 20) + (recent_engagements * 5))
        
        # 2. Vulnerability Status Score (0-30 points)
        vuln_summary = client.get_vulnerability_summary()
        total_vulns = vuln_summary['total_open'] + vuln_summary['total_fixed']
        
        if total_vulns == 0:
            score_components['vulnerability_status'] = 30  # No vulnerabilities is good
        else:
            remediation_rate = vuln_summary['total_fixed'] / total_vulns
            critical_penalty = vuln_summary['critical_open'] * 5
            high_penalty = vuln_summary['high_open'] * 3
            
            score_components['vulnerability_status'] = max(0, 
                (remediation_rate * 30) - critical_penalty - high_penalty
            )
        
        # 3. Communication Score (0-20 points) - Based on recent activity
        # This is a simplified metric - could be enhanced with actual communication data
        if current_engagements > 0:
            score_components['communication'] = 20
        elif recent_engagements > 0:
            score_components['communication'] = 10
        else:
            score_components['communication'] = 5
        
        # 4. Relationship Age Score (0-10 points)
        first_engagement = client.engagements.order_by('start_date').first()
        if first_engagement:
            relationship_days = (today - first_engagement.start_date).days
            # Longer relationships get higher scores (up to 2 years)
            score_components['relationship_age'] = min(10, relationship_days / 730 * 10)
        
        # Calculate total health score
        total_client_score = sum(score_components.values())
        health_score = round(total_client_score / 10, 2)  # Scale to 0-10
        
        # Determine if client needs attention
        needs_attention = (
            health_score < 5.0 or 
            vuln_summary['critical_open'] > 0 or
            (current_engagements == 0 and recent_engagements == 0)
        )
        
        if needs_attention:
            inactive_clients.append({
                'client': client,
                'health_score': health_score,
                'reasons': []
            })
        
        client_health_data.append({
            'client': client,
            'health_score': health_score,
            'score_components': score_components,
            'needs_attention': needs_attention
        })
        
        total_score += health_score
    
    # Calculate average health score
    average_health_score = round(total_score / len(client_health_data), 2) if client_health_data else 0
    
    result = {
        'client_health_score': average_health_score,
        'client_details': client_health_data,
        'inactive_clients': len(inactive_clients),
        'clients_needing_attention': inactive_clients[:5]  # Top 5 for performance
    }
    
    # Cache the result
    _set_cache(cache_key, result)
    return result


def generate_dashboard_alerts(start_date, end_date):
    """
    Generate actionable alerts for the manager dashboard
    """
    alerts = []
    
    # Get utilization data
    utilization_data = calculate_enhanced_team_utilization(start_date, end_date)
    
    # Underutilization alerts
    if len(utilization_data['underutilized_employees']) > 0:
        alerts.append({
            'type': 'warning',
            'category': 'utilization',
            'title': f"{len(utilization_data['underutilized_employees'])} Underutilized Team Members",
            'description': f"Employees with utilization below 40%",
            'action': 'Review workload distribution',
            'count': len(utilization_data['underutilized_employees']),
            'priority': 'medium'
        })
    
    # Over-utilization alerts
    if len(utilization_data['overutilized_employees']) > 0:
        alerts.append({
            'type': 'danger',
            'category': 'utilization',
            'title': f"{len(utilization_data['overutilized_employees'])} Overutilized Team Members",
            'description': f"Employees with utilization above 90%",
            'action': 'Consider workload rebalancing',
            'count': len(utilization_data['overutilized_employees']),
            'priority': 'high'
        })
    
    # Critical vulnerability alerts
    today = timezone.now().date()
    critical_vulns = Vulnerability.objects.filter(
        status='Open', 
        severity='Critical',
        engagement__start_date__lte=today,
        engagement__end_date__gte=today
    ).count()
    
    if critical_vulns > 0:
        alerts.append({
            'type': 'danger',
            'category': 'security',
            'title': f"{critical_vulns} Critical Vulnerabilities",
            'description': "Open critical vulnerabilities in active engagements",
            'action': 'Review and prioritize remediation',
            'count': critical_vulns,
            'priority': 'high'
        })
    
    # Capacity warnings
    if utilization_data['team_utilization'] > 85:
        alerts.append({
            'type': 'warning',
            'category': 'capacity',
            'title': 'High Team Utilization',
            'description': f"Team utilization at {utilization_data['team_utilization']}%",
            'action': 'Plan for additional resources',
            'count': 1,
            'priority': 'medium'
        })
    
    # Client health alerts
    client_health = calculate_client_health_scores()
    if len(client_health['clients_needing_attention']) > 0:
        alerts.append({
            'type': 'info',
            'category': 'client',
            'title': f"{len(client_health['clients_needing_attention'])} Clients Need Attention",
            'description': "Clients with low health scores or open critical vulnerabilities",
            'action': 'Review client relationships',
            'count': len(client_health['clients_needing_attention']),
            'priority': 'medium'
        })
    
    # Sort alerts by priority
    priority_order = {'high': 1, 'medium': 2, 'low': 3}
    alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    return alerts


def get_enhanced_manager_dashboard_data(start_date, end_date):
    """
    Main function to get all enhanced manager dashboard data
    This combines all the individual calculations for optimal performance
    """
    try:
        # Run calculations in parallel conceptually (could be optimized with threading)
        utilization_data = calculate_enhanced_team_utilization(start_date, end_date)
        financial_data = calculate_financial_intelligence(start_date, end_date)
        client_health_data = calculate_client_health_scores()
        alerts = generate_dashboard_alerts(start_date, end_date)
        
        # Get enhanced employee data for the existing chart
        employees = Employee.objects.exclude(is_active=False)
        enhanced_emp_data = []
        
        for emp in employees:
            engaged_days = emp.countEngDays(start_date, end_date)
            utilization_rate = 0
            
            # Find this employee in utilization data
            for emp_util in utilization_data['employee_details']:
                if emp_util['employee'].id == emp.id:
                    utilization_rate = emp_util['utilization_rate']
                    break
            
            enhanced_emp_data.append([
                emp, 
                engaged_days, 
                utilization_rate,
                'under' if utilization_rate < 30 else 'over' if utilization_rate > 80 else 'optimal'
            ])
        
        # Sort by engaged days (maintaining existing behavior)
        enhanced_emp_data.sort(key=lambda x: x[1])
        
        return {
            'success': True,
            'team_utilization': utilization_data['team_utilization'],
            'available_capacity': utilization_data['available_capacity'],
            'monthly_revenue': financial_data['monthly_revenue'],
            'cost_per_emp_per_day': financial_data['cost_per_emp_per_day'],
            'budget_variance': financial_data['budget_variance'],
            'client_health_score': client_health_data['client_health_score'],
            'underutilized_count': len(utilization_data['underutilized_employees']),
            'inactive_clients': client_health_data['inactive_clients'],
            'critical_vulns': sum(1 for alert in alerts if alert['category'] == 'security'),
            'action_alerts': alerts,
            'enhanced_emp_data': enhanced_emp_data,
            'financial_summary': {
                'total_cost': financial_data['total_cost'],
                'active_employees': financial_data['active_employees'],
                'total_engaged_days': financial_data['total_engaged_days']
            },
            'utilization_distribution': utilization_data['utilization_distribution']
        }
    
    except Exception as e:
        logger.error(f"Error calculating enhanced manager dashboard data: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'team_utilization': 0,
            'available_capacity': 0,
            'monthly_revenue': 0,
            'cost_per_emp_per_day': 1000,
            'budget_variance': 0,
            'client_health_score': 0,
            'underutilized_count': 0,
            'inactive_clients': 0,
            'critical_vulns': 0,
            'action_alerts': [],
            'enhanced_emp_data': [],
            'financial_summary': {},
            'utilization_distribution': {}
        }