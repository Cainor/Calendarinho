"""
Advanced Filtering and Bulk Operations API Module for Phase 2 Backend Features

This module provides advanced filtering capabilities, bulk operations, and optimized
data structures for the enhanced UI components.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max, Min, Avg
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json
import datetime
from typing import Dict, List, Any, Optional

from .models import Engagement, Client, Vulnerability
from .forms import (
    AdvancedEmployeeFilterForm, AdvancedClientFilterForm, 
    AdvancedEngagementFilterForm, VulnerabilityFilterForm, BulkActionForm
)
from .service import get_enhanced_employee_data, get_enhanced_client_data, get_enhanced_engagement_data
from users.models import CustomUser as Employee


def apply_employee_filters(queryset_data: List[Dict], filters: Dict) -> List[Dict]:
    """Apply advanced filters to employee data"""
    filtered_data = queryset_data
    
    # Text search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered_data = [
            emp for emp in filtered_data
            if search_term in emp['full_name'].lower()
        ]
    
    # Status filter
    if filters.get('status'):
        filtered_data = [
            emp for emp in filtered_data
            if emp['status_type'] == filters['status']
        ]
    
    # Availability filter
    if filters.get('availability'):
        filtered_data = [
            emp for emp in filtered_data
            if emp['availability_status'] == filters['availability']
        ]
    
    # User type filter
    if filters.get('user_type'):
        filtered_data = [
            emp for emp in filtered_data
            if emp['user_type'] == filters['user_type']
        ]
    
    # Utilization range filters
    if filters.get('min_utilization') is not None:
        min_util = float(filters['min_utilization'])
        filtered_data = [
            emp for emp in filtered_data
            if emp['utilization_rate'] >= min_util
        ]
    
    if filters.get('max_utilization') is not None:
        max_util = float(filters['max_utilization'])
        filtered_data = [
            emp for emp in filtered_data
            if emp['utilization_rate'] <= max_util
        ]
    
    # Engagement count filters
    if filters.get('min_engagements') is not None:
        min_eng = int(filters['min_engagements'])
        filtered_data = [
            emp for emp in filtered_data
            if emp['current_engagements'] >= min_eng
        ]
    
    if filters.get('max_engagements') is not None:
        max_eng = int(filters['max_engagements'])
        filtered_data = [
            emp for emp in filtered_data
            if emp['current_engagements'] <= max_eng
        ]
    
    # Date filters for next event
    if filters.get('next_event_from') or filters.get('next_event_to'):
        from_date = filters.get('next_event_from')
        to_date = filters.get('next_event_to')
        
        def date_in_range(emp_start_date):
            if not emp_start_date:
                return False
            if isinstance(emp_start_date, str):
                emp_start_date = datetime.datetime.fromisoformat(emp_start_date.replace('Z', '+00:00')).date()
            elif hasattr(emp_start_date, 'date'):
                emp_start_date = emp_start_date.date()
            
            if from_date and emp_start_date < from_date:
                return False
            if to_date and emp_start_date > to_date:
                return False
            return True
        
        filtered_data = [
            emp for emp in filtered_data
            if date_in_range(emp.get('start_date'))
        ]
    
    return filtered_data


def apply_client_filters(queryset_data: List[Dict], filters: Dict) -> List[Dict]:
    """Apply advanced filters to client data"""
    filtered_data = queryset_data
    
    # Text search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered_data = [
            client for client in filtered_data
            if (search_term in client['name'].lower() or 
                search_term in client['acronym'].lower())
        ]
    
    # Activity level filter
    if filters.get('activity_level'):
        filtered_data = [
            client for client in filtered_data
            if client['activity_level'] == filters['activity_level']
        ]
    
    # Risk level filter (calculated from risk score)
    if filters.get('risk_level'):
        def get_risk_level(risk_score):
            if risk_score >= 50:
                return 'high'
            elif risk_score >= 20:
                return 'medium'
            elif risk_score > 0:
                return 'low'
            else:
                return 'none'
        
        target_risk = filters['risk_level']
        filtered_data = [
            client for client in filtered_data
            if get_risk_level(client['risk_score']) == target_risk
        ]
    
    # Boolean filters
    if filters.get('has_open_vulnerabilities'):
        filtered_data = [
            client for client in filtered_data
            if client['vulnerabilities']['total_open'] > 0
        ]
    
    if filters.get('has_active_engagements'):
        filtered_data = [
            client for client in filtered_data
            if client['current_engagements'] > 0
        ]
    
    # Range filters
    if filters.get('min_engagements') is not None:
        min_eng = int(filters['min_engagements'])
        filtered_data = [
            client for client in filtered_data
            if client['total_engagements'] >= min_eng
        ]
    
    if filters.get('max_engagements') is not None:
        max_eng = int(filters['max_engagements'])
        filtered_data = [
            client for client in filtered_data
            if client['total_engagements'] <= max_eng
        ]
    
    if filters.get('min_risk_score') is not None:
        min_risk = int(filters['min_risk_score'])
        filtered_data = [
            client for client in filtered_data
            if client['risk_score'] >= min_risk
        ]
    
    if filters.get('max_risk_score') is not None:
        max_risk = int(filters['max_risk_score'])
        filtered_data = [
            client for client in filtered_data
            if client['risk_score'] <= max_risk
        ]
    
    # Date filters
    if filters.get('last_engagement_from') or filters.get('last_engagement_to'):
        from_date = filters.get('last_engagement_from')
        to_date = filters.get('last_engagement_to')
        
        def date_in_range(last_date):
            if not last_date:
                return False
            if isinstance(last_date, str):
                last_date = datetime.datetime.fromisoformat(last_date.replace('Z', '+00:00')).date()
            elif hasattr(last_date, 'date'):
                last_date = last_date.date()
            
            if from_date and last_date < from_date:
                return False
            if to_date and last_date > to_date:
                return False
            return True
        
        filtered_data = [
            client for client in filtered_data
            if date_in_range(client.get('last_engagement_date'))
        ]
    
    return filtered_data


def apply_engagement_filters(queryset_data: List[Dict], filters: Dict) -> List[Dict]:
    """Apply advanced filters to engagement data"""
    filtered_data = queryset_data
    
    # Text search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered_data = [
            eng for eng in filtered_data
            if (search_term in eng['name'].lower() or 
                search_term in eng['clientName'].lower())
        ]
    
    # Status filter
    if filters.get('status'):
        filtered_data = [
            eng for eng in filtered_data
            if eng['status'] == filters['status']
        ]
    
    # Priority filter (calculated from priority score)
    if filters.get('priority'):
        def get_priority_level(priority_score):
            if priority_score >= 15:
                return 'high'
            elif priority_score >= 5:
                return 'medium'
            else:
                return 'low'
        
        target_priority = filters['priority']
        filtered_data = [
            eng for eng in filtered_data
            if get_priority_level(eng['priority_score']) == target_priority
        ]
    
    # Client filter
    if filters.get('client'):
        client_id = int(filters['client'])
        filtered_data = [
            eng for eng in filtered_data
            if eng['clientID'] == client_id
        ]
    
    # Service type filter
    if filters.get('service_type'):
        service_name = filters['service_type']
        filtered_data = [
            eng for eng in filtered_data
            if eng['serviceType'] == service_name
        ]
    
    # Boolean filters
    if filters.get('has_vulnerabilities'):
        filtered_data = [
            eng for eng in filtered_data
            if eng['vulnerabilities']['total_open'] > 0
        ]
    
    if filters.get('ending_soon'):
        today = timezone.now().date()
        filtered_data = [
            eng for eng in filtered_data
            if (eng['status'] == 'ongoing' and 
                (eng['endDate'] - today).days <= 7)
        ]
    
    # Range filters
    if filters.get('min_duration') is not None:
        min_dur = int(filters['min_duration'])
        filtered_data = [
            eng for eng in filtered_data
            if eng['duration_days'] >= min_dur
        ]
    
    if filters.get('max_duration') is not None:
        max_dur = int(filters['max_duration'])
        filtered_data = [
            eng for eng in filtered_data
            if eng['duration_days'] <= max_dur
        ]
    
    if filters.get('min_risk_score') is not None:
        min_risk = int(filters['min_risk_score'])
        filtered_data = [
            eng for eng in filtered_data
            if eng['risk_score'] >= min_risk
        ]
    
    if filters.get('max_risk_score') is not None:
        max_risk = int(filters['max_risk_score'])
        filtered_data = [
            eng for eng in filtered_data
            if eng['risk_score'] <= max_risk
        ]
    
    # Date filters
    date_filters = [
        ('start_date_from', 'start_date_to', 'startDate'),
        ('end_date_from', 'end_date_to', 'endDate')
    ]
    
    for from_key, to_key, date_field in date_filters:
        if filters.get(from_key) or filters.get(to_key):
            from_date = filters.get(from_key)
            to_date = filters.get(to_key)
            
            def date_in_range(eng_date):
                if isinstance(eng_date, str):
                    eng_date = datetime.datetime.fromisoformat(eng_date.replace('Z', '+00:00')).date()
                elif hasattr(eng_date, 'date'):
                    eng_date = eng_date.date()
                
                if from_date and eng_date < from_date:
                    return False
                if to_date and eng_date > to_date:
                    return False
                return True
            
            filtered_data = [
                eng for eng in filtered_data
                if date_in_range(eng[date_field])
            ]
    
    return filtered_data


def paginate_data(data: List[Dict], page: int = 1, per_page: int = 25) -> Dict:
    """Paginate data with metadata"""
    paginator = Paginator(data, per_page)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return {
        'data': list(page_obj),
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'per_page': per_page,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        }
    }


@login_required
def api_employees_filtered(request):
    """Advanced filtered employees API endpoint"""
    # Get filter parameters
    form = AdvancedEmployeeFilterForm(request.GET)
    filters = {}
    
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v is not None and v != ''}
    
    # Get base data
    base_data = get_enhanced_employee_data()
    employees = base_data['employees']
    
    # Apply filters
    filtered_employees = apply_employee_filters(employees, filters)
    
    # Sort options
    sort_by = request.GET.get('sort_by', 'full_name')
    sort_order = request.GET.get('sort_order', 'asc')
    
    if sort_by in ['full_name', 'status_type', 'utilization_rate', 'current_engagements']:
        reverse_sort = sort_order == 'desc'
        filtered_employees.sort(
            key=lambda x: x.get(sort_by, ''), 
            reverse=reverse_sort
        )
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    
    paginated_data = paginate_data(filtered_employees, page, per_page)
    
    return JsonResponse({
        'success': True,
        'employees': paginated_data['data'],
        'pagination': paginated_data['pagination'],
        'summary': {
            'total_filtered': len(filtered_employees),
            'total_unfiltered': len(employees),
            'employee_counts': base_data['employee_counts'],
            'filters_applied': len([k for k, v in filters.items() if v])
        }
    })


@login_required
def api_clients_filtered(request):
    """Advanced filtered clients API endpoint"""
    # Get filter parameters
    form = AdvancedClientFilterForm(request.GET)
    filters = {}
    
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v is not None and v != ''}
    
    # Get base data
    base_data = get_enhanced_client_data()
    clients = base_data['clients']
    
    # Apply filters
    filtered_clients = apply_client_filters(clients, filters)
    
    # Sort options
    sort_by = request.GET.get('sort_by', 'name')
    sort_order = request.GET.get('sort_order', 'asc')
    
    if sort_by in ['name', 'activity_level', 'risk_score', 'total_engagements']:
        reverse_sort = sort_order == 'desc'
        filtered_clients.sort(
            key=lambda x: x.get(sort_by, ''), 
            reverse=reverse_sort
        )
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    
    paginated_data = paginate_data(filtered_clients, page, per_page)
    
    return JsonResponse({
        'success': True,
        'clients': paginated_data['data'],
        'pagination': paginated_data['pagination'],
        'summary': {
            'total_filtered': len(filtered_clients),
            'total_unfiltered': len(clients),
            'client_stats': base_data['client_stats'],
            'filters_applied': len([k for k, v in filters.items() if v])
        }
    })


@login_required
def api_engagements_filtered(request):
    """Advanced filtered engagements API endpoint"""
    # Get filter parameters
    form = AdvancedEngagementFilterForm(request.GET)
    filters = {}
    
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v is not None and v != ''}
    
    # Get base data
    base_data = get_enhanced_engagement_data()
    engagements = base_data['engagements']
    
    # Apply filters
    filtered_engagements = apply_engagement_filters(engagements, filters)
    
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
            'total_unfiltered': len(engagements),
            'engagement_stats': base_data['engagement_stats'],
            'filters_applied': len([k for k, v in filters.items() if v])
        }
    })


@login_required
def api_vulnerabilities_filtered(request):
    """Advanced filtered vulnerabilities API endpoint"""
    # Get filter parameters
    form = VulnerabilityFilterForm(request.GET)
    filters = {}
    
    if form.is_valid():
        filters = {k: v for k, v in form.cleaned_data.items() if v is not None and v != ''}
    
    # Build queryset with optimizations
    queryset = Vulnerability.objects.select_related(
        'engagement__client', 'created_by', 'fixed_by'
    ).all()
    
    # Apply filters to queryset
    if filters.get('search'):
        search_term = filters['search']
        queryset = queryset.filter(
            Q(title__icontains=search_term) | 
            Q(description__icontains=search_term)
        )
    
    if filters.get('severity'):
        queryset = queryset.filter(severity=filters['severity'])
    
    if filters.get('status'):
        queryset = queryset.filter(status=filters['status'])
    
    if filters.get('engagement'):
        queryset = queryset.filter(engagement=filters['engagement'])
    
    if filters.get('created_by'):
        queryset = queryset.filter(created_by=filters['created_by'])
    
    # Date filters
    if filters.get('created_from'):
        queryset = queryset.filter(created_at__date__gte=filters['created_from'])
    
    if filters.get('created_to'):
        queryset = queryset.filter(created_at__date__lte=filters['created_to'])
    
    if filters.get('fixed_from'):
        queryset = queryset.filter(fixed_at__date__gte=filters['fixed_from'])
    
    if filters.get('fixed_to'):
        queryset = queryset.filter(fixed_at__date__lte=filters['fixed_to'])
    
    # Overdue filter
    if filters.get('overdue_only'):
        today = timezone.now().date()
        severity_sla = {
            'Critical': 7,
            'High': 30,
            'Medium': 90,
            'Low': 180
        }
        
        overdue_conditions = Q()
        for severity, days in severity_sla.items():
            cutoff_date = today - timezone.timedelta(days=days)
            overdue_conditions |= Q(
                severity=severity,
                status='Open',
                created_at__date__lte=cutoff_date
            )
        
        queryset = queryset.filter(overdue_conditions)
    
    # Sort options
    sort_by = request.GET.get('sort_by', 'created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Custom sorting for severity
    if sort_by == 'severity':
        severity_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
        if sort_order == 'desc':
            queryset = sorted(queryset, key=lambda v: severity_order.get(v.severity, 5))
        else:
            queryset = sorted(queryset, key=lambda v: severity_order.get(v.severity, 5), reverse=True)
    else:
        order_prefix = '-' if sort_order == 'desc' else ''
        queryset = queryset.order_by(f'{order_prefix}{sort_by}')
    
    # Convert to list for pagination
    vulnerabilities_data = []
    for vuln in queryset:
        vuln_data = {
            'id': vuln.id,
            'title': vuln.title,
            'description': vuln.description[:100] + '...' if len(vuln.description) > 100 else vuln.description,
            'severity': vuln.severity,
            'status': vuln.status,
            'engagement_name': vuln.engagement.name,
            'engagement_id': vuln.engagement.id,
            'client_name': vuln.engagement.client.name,
            'created_by_name': vuln.created_by.get_full_name(),
            'created_at': vuln.created_at.isoformat(),
            'fixed_at': vuln.fixed_at.isoformat() if vuln.fixed_at else None,
            'fixed_by_name': vuln.fixed_by.get_full_name() if vuln.fixed_by else None,
            'severity_color': vuln.get_severity_color(),
            'severity_icon': vuln.get_severity_icon(),
            'is_overdue': vuln.is_overdue(),
            'days_to_fix': vuln.days_to_fix(),
        }
        vulnerabilities_data.append(vuln_data)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    
    paginated_data = paginate_data(vulnerabilities_data, page, per_page)
    
    # Summary statistics
    total_count = len(vulnerabilities_data)
    severity_counts = {}
    status_counts = {}
    
    for vuln in vulnerabilities_data:
        severity_counts[vuln['severity']] = severity_counts.get(vuln['severity'], 0) + 1
        status_counts[vuln['status']] = status_counts.get(vuln['status'], 0) + 1
    
    return JsonResponse({
        'success': True,
        'vulnerabilities': paginated_data['data'],
        'pagination': paginated_data['pagination'],
        'summary': {
            'total_filtered': total_count,
            'severity_counts': severity_counts,
            'status_counts': status_counts,
            'filters_applied': len([k for k, v in filters.items() if v])
        }
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_bulk_vulnerability_update(request):
    """Bulk update vulnerabilities status"""
    try:
        data = json.loads(request.body)
        vulnerability_ids = data.get('vulnerability_ids', [])
        new_status = data.get('new_status')
        
        if not vulnerability_ids or not new_status:
            return JsonResponse({
                'success': False,
                'error': 'Missing vulnerability_ids or new_status'
            }, status=400)
        
        if new_status not in ['Open', 'Fixed']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status. Must be Open or Fixed'
            }, status=400)
        
        # Get vulnerabilities and check permissions
        vulnerabilities = Vulnerability.objects.filter(id__in=vulnerability_ids)
        
        # Check if user has permission to modify all vulnerabilities
        for vuln in vulnerabilities:
            if not (request.user == vuln.created_by or request.user.is_superuser or 
                    request.user.user_type == 'M'):
                return JsonResponse({
                    'success': False,
                    'error': f'Permission denied for vulnerability: {vuln.title}'
                }, status=403)
        
        # Perform bulk update
        updated_count = 0
        for vuln in vulnerabilities:
            if vuln.status != new_status:
                vuln.status = new_status
                if new_status == 'Fixed':
                    vuln.fixed_at = timezone.now()
                    vuln.fixed_by = request.user
                else:
                    vuln.fixed_at = None
                    vuln.fixed_by = None
                vuln.save()
                updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully updated {updated_count} vulnerabilities to {new_status}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def api_bulk_vulnerability_delete(request):
    """Bulk delete vulnerabilities"""
    try:
        data = json.loads(request.body)
        vulnerability_ids = data.get('vulnerability_ids', [])
        confirm = data.get('confirm', False)
        
        if not vulnerability_ids:
            return JsonResponse({
                'success': False,
                'error': 'Missing vulnerability_ids'
            }, status=400)
        
        if not confirm:
            return JsonResponse({
                'success': False,
                'error': 'Confirmation required for bulk delete'
            }, status=400)
        
        # Get vulnerabilities and check permissions
        vulnerabilities = Vulnerability.objects.filter(id__in=vulnerability_ids)
        
        # Check if user has permission to delete all vulnerabilities
        for vuln in vulnerabilities:
            if not (request.user == vuln.created_by or request.user.is_superuser or 
                    request.user.user_type == 'M'):
                return JsonResponse({
                    'success': False,
                    'error': f'Permission denied to delete vulnerability: {vuln.title}'
                }, status=403)
        
        # Perform bulk delete
        deleted_count = vulnerabilities.count()
        vulnerabilities.delete()
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} vulnerabilities'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_mobile_optimized_data(request):
    """Mobile-optimized data endpoint with compact structures"""
    data_type = request.GET.get('type', 'dashboard')
    
    if data_type == 'dashboard':
        # Compact dashboard data for mobile
        from .service import get_dashboard_summary
        dashboard_data = get_dashboard_summary()
        
        # Ongoing engagements with minimal data
        ongoing_engagements = Engagement.get_ongoing_engagements()[:5]  # Limit to 5 for mobile
        compact_engagements = []
        
        for eng in ongoing_engagements:
            compact_engagements.append({
                'id': eng.id,
                'name': eng.name[:30] + '...' if len(eng.name) > 30 else eng.name,
                'client': eng.client.acronym,
                'progress': eng.days_left_percentage(),
                'priority': 'high' if eng.get_vulnerability_risk_score() > 20 else 'normal'
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'summary': dashboard_data,
                'ongoing_engagements': compact_engagements,
                'alerts': []  # Could add alerts for overdue items, etc.
            }
        })
    
    elif data_type == 'engagements':
        # Mobile-optimized engagements list
        engagements_data = get_enhanced_engagement_data()
        mobile_engagements = []
        
        for eng in engagements_data['engagements'][:20]:  # Limit to 20 for mobile
            mobile_engagements.append({
                'id': eng['engID'],
                'title': eng['name'],
                'subtitle': f"{eng['clientName']} • {eng['serviceType']}",
                'status': eng['status'],
                'progress': eng['progress_percentage'],
                'priority': 'high' if eng['priority_score'] > 15 else 'normal',
                'due_date': eng['endDate'],
                'team_size': eng['employee_count'],
                'risk_level': 'high' if eng['risk_score'] > 20 else 'low'
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'engagements': mobile_engagements,
                'stats': engagements_data['engagement_stats']
            }
        })
    
    elif data_type == 'clients':
        # Mobile-optimized clients list
        clients_data = get_enhanced_client_data()
        mobile_clients = []
        
        for client in clients_data['clients'][:20]:  # Limit to 20 for mobile
            mobile_clients.append({
                'id': client['cliID'],
                'name': client['name'],
                'acronym': client['acronym'],
                'activity': client['activity_level'],
                'engagements': client['current_engagements'],
                'risk_score': client['risk_score'],
                'last_engagement': client['last_engagement_date']
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'clients': mobile_clients,
                'stats': clients_data['client_stats']
            }
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid data type'
        }, status=400)


@login_required
def api_filter_options(request):
    """Get available filter options for dropdowns"""
    filter_type = request.GET.get('type')
    
    if filter_type == 'employees':
        return JsonResponse({
            'success': True,
            'options': {
                'statuses': ['Available', 'Engaged', 'Training', 'Vacation'],
                'user_types': [{'value': 'E', 'label': 'Employee'}, {'value': 'M', 'label': 'Manager'}],
                'availability': ['available', 'unavailable', 'partially_available']
            }
        })
    
    elif filter_type == 'clients':
        return JsonResponse({
            'success': True,
            'options': {
                'activity_levels': ['high', 'medium', 'low'],
                'risk_levels': ['high', 'medium', 'low', 'none']
            }
        })
    
    elif filter_type == 'engagements':
        clients = [{'value': c.id, 'label': c.name} for c in Client.objects.all()]
        services = [{'value': s.id, 'label': s.name} for s in Service.objects.all()]
        employees = [{'value': e.id, 'label': e.get_full_name()} for e in Employee.objects.filter(is_active=True)]
        
        return JsonResponse({
            'success': True,
            'options': {
                'statuses': ['ongoing', 'future', 'completed'],
                'priorities': ['high', 'medium', 'low'],
                'clients': clients,
                'services': services,
                'employees': employees
            }
        })
    
    elif filter_type == 'vulnerabilities':
        engagements = [{'value': e.id, 'label': f"{e.name} ({e.client.name})"} for e in Engagement.objects.select_related('client')]
        employees = [{'value': e.id, 'label': e.get_full_name()} for e in Employee.objects.filter(is_active=True)]
        
        return JsonResponse({
            'success': True,
            'options': {
                'severities': ['Critical', 'High', 'Medium', 'Low'],
                'statuses': ['Open', 'Fixed'],
                'engagements': engagements,
                'employees': employees
            }
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid filter type'
        }, status=400)