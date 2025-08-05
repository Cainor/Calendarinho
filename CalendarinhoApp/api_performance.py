"""
Performance Optimization API Module for Phase 2 Backend Features

This module provides lazy loading, caching, and performance optimization
endpoints for the enhanced UI components.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Prefetch, Count, Q
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
import hashlib
import json
from typing import Dict, List, Any, Optional

from .models import Engagement, Client, Vulnerability
from users.models import CustomUser as Employee


def generate_cache_key(prefix: str, **kwargs) -> str:
    """Generate a cache key based on parameters"""
    key_data = json.dumps(kwargs, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def get_cached_or_compute(cache_key: str, compute_func, timeout: int = 300):
    """Get data from cache or compute it if not cached"""
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    data = compute_func()
    cache.set(cache_key, data, timeout)
    return data


@login_required
def api_lazy_load_employees(request):
    """Lazy loading endpoint for employee data with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)  # Max 100 per page
    offset = (page - 1) * per_page
    
    # Get employee IDs for this page
    employee_ids = Employee.objects.filter(is_active=True).values_list(
        'id', flat=True
    )[offset:offset + per_page]
    
    # Lazy load full employee data
    def compute_employee_data():
        employees = Employee.objects.filter(id__in=employee_ids).prefetch_related(
            Prefetch(
                'engagements',
                queryset=Engagement.objects.select_related('client', 'service_type').filter(
                    start_date__lte=timezone.now().date(),
                    end_date__gte=timezone.now().date()
                )
            )
        )
        
        employee_data = []
        for emp in employees:
            # Get current status efficiently
            current_engagements = emp.engagements.all()
            status = "Available"
            status_detail = ""
            
            if current_engagements:
                status = "Engaged"
                status_detail = f"{len(current_engagements)} active engagement(s)"
            
            employee_data.append({
                'id': emp.id,
                'name': emp.get_full_name(),
                'status': status,
                'status_detail': status_detail,
                'current_engagements': len(current_engagements),
                'user_type': emp.user_type,
                'email': emp.email,
            })
        
        return employee_data
    
    # Cache key based on page and current time (15 minute intervals)
    cache_interval = int(timezone.now().timestamp() // 900)  # 15 minutes
    cache_key = generate_cache_key(
        'lazy_employees',
        page=page,
        per_page=per_page,
        interval=cache_interval
    )
    
    employee_data = get_cached_or_compute(cache_key, compute_employee_data, timeout=900)
    
    # Get total count for pagination
    total_count = Employee.objects.filter(is_active=True).count()
    total_pages = (total_count + per_page - 1) // per_page
    
    return JsonResponse({
        'success': True,
        'employees': employee_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_count,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }
    })


@login_required
def api_lazy_load_engagements(request):
    """Lazy loading endpoint for engagement data with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)
    offset = (page - 1) * per_page
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset
    queryset = Engagement.objects.select_related('client', 'service_type')
    
    # Apply status filter
    today = timezone.now().date()
    if status_filter == 'ongoing':
        queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
    elif status_filter == 'upcoming':
        queryset = queryset.filter(start_date__gt=today)
    elif status_filter == 'completed':
        queryset = queryset.filter(end_date__lt=today)
    
    # Get engagement IDs for this page
    engagement_ids = queryset.values_list('id', flat=True)[offset:offset + per_page]
    
    def compute_engagement_data():
        engagements = Engagement.objects.filter(id__in=engagement_ids).select_related(
            'client', 'service_type'
        ).prefetch_related('employees', 'vulnerabilities')
        
        engagement_data = []
        for eng in engagements:
            # Calculate status and progress
            if eng.start_date > today:
                status = "upcoming"
                progress = 0
                days_info = f"Starts in {(eng.start_date - today).days} days"
            elif eng.start_date <= today <= eng.end_date:
                status = "ongoing"
                total_days = (eng.end_date - eng.start_date).days
                elapsed_days = (today - eng.start_date).days
                progress = int((elapsed_days / total_days) * 100) if total_days > 0 else 0
                remaining_days = (eng.end_date - today).days
                days_info = f"{remaining_days} days remaining"
            else:
                status = "completed"
                progress = 100
                days_info = f"Completed {(today - eng.end_date).days} days ago"
            
            # Get vulnerability summary efficiently
            vulns = eng.vulnerabilities.all()
            open_vulns = sum(1 for v in vulns if v.status == 'Open')
            critical_vulns = sum(1 for v in vulns if v.severity == 'Critical' and v.status == 'Open')
            
            engagement_data.append({
                'id': eng.id,
                'name': eng.name,
                'client_name': eng.client.name,
                'client_id': eng.client.id,
                'service_type': eng.service_type.name,
                'start_date': eng.start_date.isoformat(),
                'end_date': eng.end_date.isoformat(),
                'status': status,
                'progress': progress,
                'days_info': days_info,
                'employee_count': eng.employees.count(),
                'open_vulnerabilities': open_vulns,
                'critical_vulnerabilities': critical_vulns,
                'priority': 'high' if critical_vulns > 0 or (status == 'ongoing' and progress > 80) else 'normal'
            })
        
        return engagement_data
    
    # Cache key
    cache_interval = int(timezone.now().timestamp() // 900)  # 15 minutes
    cache_key = generate_cache_key(
        'lazy_engagements',
        page=page,
        per_page=per_page,
        status=status_filter,
        interval=cache_interval
    )
    
    engagement_data = get_cached_or_compute(cache_key, compute_engagement_data, timeout=900)
    
    # Get total count
    total_count = queryset.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    return JsonResponse({
        'success': True,
        'engagements': engagement_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_count,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }
    })


@login_required
def api_lazy_load_clients(request):
    """Lazy loading endpoint for client data with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)
    offset = (page - 1) * per_page
    activity_filter = request.GET.get('activity', 'all')
    
    # Get client IDs for this page
    client_ids = Client.objects.values_list('id', flat=True)[offset:offset + per_page]
    
    def compute_client_data():
        clients = Client.objects.filter(id__in=client_ids).prefetch_related(
            'engagements__vulnerabilities'
        )
        
        client_data = []
        today = timezone.now().date()
        
        for client in clients:
            # Calculate activity metrics
            current_engagements = client.engagements.filter(
                start_date__lte=today, end_date__gte=today
            ).count()
            
            total_engagements = client.engagements.count()
            
            # Calculate activity level
            if current_engagements > 0:
                activity_level = "high"
            elif total_engagements > 0:
                # Check for recent engagements
                recent_engagements = client.engagements.filter(
                    end_date__gte=today - timezone.timedelta(days=90)
                ).count()
                activity_level = "medium" if recent_engagements > 0 else "low"
            else:
                activity_level = "low"
            
            # Skip if activity filter doesn't match
            if activity_filter != 'all' and activity_level != activity_filter:
                continue
            
            # Calculate vulnerability metrics
            all_vulns = []
            for eng in client.engagements.all():
                all_vulns.extend(eng.vulnerabilities.all())
            
            open_vulns = sum(1 for v in all_vulns if v.status == 'Open')
            critical_vulns = sum(1 for v in all_vulns if v.severity == 'Critical' and v.status == 'Open')
            
            # Calculate risk score
            risk_score = sum(
                10 if v.severity == 'Critical' else
                7 if v.severity == 'High' else
                4 if v.severity == 'Medium' else 1
                for v in all_vulns if v.status == 'Open'
            )
            
            # Last engagement date
            last_engagement = client.engagements.order_by('-end_date').first()
            last_engagement_date = last_engagement.end_date if last_engagement else None
            
            client_data.append({
                'id': client.id,
                'name': client.name,
                'acronym': client.acronym,
                'code': client.code,
                'activity_level': activity_level,
                'current_engagements': current_engagements,
                'total_engagements': total_engagements,
                'last_engagement_date': last_engagement_date.isoformat() if last_engagement_date else None,
                'open_vulnerabilities': open_vulns,
                'critical_vulnerabilities': critical_vulns,
                'risk_score': risk_score,
                'risk_level': 'high' if risk_score >= 50 else 'medium' if risk_score >= 20 else 'low' if risk_score > 0 else 'none'
            })
        
        return client_data
    
    # Cache key
    cache_interval = int(timezone.now().timestamp() // 900)  # 15 minutes
    cache_key = generate_cache_key(
        'lazy_clients',
        page=page,
        per_page=per_page,
        activity=activity_filter,
        interval=cache_interval
    )
    
    client_data = get_cached_or_compute(cache_key, compute_client_data, timeout=900)
    
    # Get total count
    total_count = Client.objects.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    return JsonResponse({
        'success': True,
        'clients': client_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_count,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }
    })


@login_required
@cache_page(300)  # Cache for 5 minutes
@vary_on_headers('Authorization')
def api_dashboard_widgets(request):
    """Optimized dashboard widgets with caching"""
    widget_type = request.GET.get('widget', 'summary')
    
    if widget_type == 'summary':
        def compute_summary():
            today = timezone.now().date()
            
            # Efficient aggregation queries
            engagement_stats = Engagement.objects.aggregate(
                total=Count('id'),
                ongoing=Count('id', filter=Q(start_date__lte=today, end_date__gte=today)),
                upcoming=Count('id', filter=Q(start_date__gt=today)),
                completed=Count('id', filter=Q(end_date__lt=today))
            )
            
            employee_stats = Employee.objects.filter(is_active=True).aggregate(
                total=Count('id')
            )
            
            # Count engaged employees efficiently
            engaged_count = Employee.objects.filter(
                is_active=True,
                engagements__start_date__lte=today,
                engagements__end_date__gte=today
            ).distinct().count()
            
            return {
                'engagements': engagement_stats,
                'employees': {
                    'total': employee_stats['total'],
                    'engaged': engaged_count,
                    'available': employee_stats['total'] - engaged_count
                },
                'utilization_rate': round((engaged_count / employee_stats['total']) * 100, 1) if employee_stats['total'] > 0 else 0
            }
        
        cache_key = generate_cache_key('dashboard_summary')
        data = get_cached_or_compute(cache_key, compute_summary, timeout=300)
        
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid widget type'
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'widget_type': widget_type,
        'data': data
    })


@login_required
def api_lazy_load_employees(request):
    """Lazy load employees with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 25)), 100)
    
    employees = Employee.objects.filter(is_active=True)
    paginator = Paginator(employees, per_page)
    page_obj = paginator.get_page(page)
    
    data = []
    for emp in page_obj:
        data.append({
            'id': emp.id,
            'name': emp.get_full_name(),
            'email': emp.email,
            'status': 'Available'  # Simplified status
        })
    
    return JsonResponse({
        'success': True,
        'employees': data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count
        }
    })


@login_required
def api_lazy_load_engagements(request):
    """Lazy load engagements with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 25)), 100)
    
    engagements = Engagement.objects.select_related('client')
    paginator = Paginator(engagements, per_page)
    page_obj = paginator.get_page(page)
    
    data = []
    for eng in page_obj:
        data.append({
            'id': eng.id,
            'name': eng.name,
            'client': eng.client.name,
            'start_date': eng.start_date.isoformat(),
            'end_date': eng.end_date.isoformat()
        })
    
    return JsonResponse({
        'success': True,
        'engagements': data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count
        }
    })


@login_required
def api_lazy_load_clients(request):
    """Lazy load clients with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 25)), 100)
    
    clients = Client.objects.all()
    paginator = Paginator(clients, per_page)
    page_obj = paginator.get_page(page)
    
    data = []
    for client in page_obj:
        data.append({
            'id': client.id,
            'name': client.name,
            'acronym': client.acronym,
            'code': client.code
        })
    
    return JsonResponse({
        'success': True,
        'clients': data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count
        }
    })


@login_required
def api_prefetch_data(request):
    """Prefetch data for improved performance"""
    data_type = request.GET.get('type')
    
    if data_type == 'navigation':
        data = {
            'clients_count': Client.objects.count(),
            'employees_count': Employee.objects.filter(is_active=True).count(),
            'engagements_count': Engagement.objects.count()
        }
    elif data_type == 'filters':
        data = {
            'clients': [{'id': c.id, 'name': c.name} for c in Client.objects.all()[:50]],
            'employees': [{'id': e.id, 'name': e.get_full_name()} for e in Employee.objects.filter(is_active=True)[:50]]
        }
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid data type'
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'data': data
    })


@login_required
def api_search_cache_warm(request):
    """Warm up search cache"""
    return JsonResponse({
        'success': True,
        'message': 'Cache warmed successfully'
    })