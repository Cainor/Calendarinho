"""
Vulnerabilities management views with advanced filtering and bulk operations
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json

from .models import Vulnerability, Engagement, Client
from .forms import VulnerabilityFilterForm, BulkActionForm
from users.models import CustomUser as Employee
from .views import not_found
from .service import get_vulnerability_analytics


@login_required
def vulnerabilities_table(request):
    """Main vulnerabilities table view with advanced filtering"""
    from .forms import VulnerabilityFilterForm
    
    # Initialize filter form
    filter_form = VulnerabilityFilterForm(request.GET or None)
    
    # Get base queryset with optimizations
    queryset = Vulnerability.objects.select_related(
        'engagement__client', 'created_by', 'fixed_by'
    ).all()
    
    # Apply filters if form is valid
    filters = {}
    if filter_form.is_valid():
        filters = {k: v for k, v in filter_form.cleaned_data.items() if v is not None and v != ''}
    
    # If this is an AJAX request, return filtered JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from .api_filters import api_vulnerabilities_filtered
        return api_vulnerabilities_filtered(request)
    
    # For regular requests, get basic data for initial page load
    recent_vulnerabilities = queryset.order_by('-created_at')[:10]
    
    # Summary statistics
    total_count = queryset.count()
    severity_counts = {
        'Critical': queryset.filter(severity='Critical').count(),
        'High': queryset.filter(severity='High').count(),
        'Medium': queryset.filter(severity='Medium').count(),
        'Low': queryset.filter(severity='Low').count(),
    }
    status_counts = {
        'Open': queryset.filter(status='Open').count(),
        'Fixed': queryset.filter(status='Fixed').count(),
    }
    
    # Overdue vulnerabilities count
    today = timezone.now().date()
    severity_sla = {
        'Critical': 7,
        'High': 30,
        'Medium': 90,
        'Low': 180
    }
    
    overdue_count = 0
    for severity, days in severity_sla.items():
        cutoff_date = today - timezone.timedelta(days=days)
        overdue_count += queryset.filter(
            severity=severity,
            status='Open',
            created_at__date__lte=cutoff_date
        ).count()
    
    context = {
        'filter_form': filter_form,
        'recent_vulnerabilities': recent_vulnerabilities,
        'total_count': total_count,
        'severity_counts': severity_counts,
        'status_counts': status_counts,
        'overdue_count': overdue_count,
        'bulk_form': BulkActionForm(),
    }
    
    return render(request, "CalendarinhoApp/VulnerabilitiesTable.html", context)


@login_required
def vulnerability_detail(request, vuln_id):
    """Detailed view of a single vulnerability"""
    vulnerability = get_object_or_404(Vulnerability, id=vuln_id)
    
    # Check if user can view this vulnerability
    if not (request.user in vulnerability.engagement.employees.all() or 
            request.user.is_superuser or request.user.user_type == 'M'):
        return not_found(request)
    
    # Get related vulnerabilities in the same engagement
    related_vulnerabilities = vulnerability.engagement.vulnerabilities.exclude(
        id=vulnerability.id
    ).order_by('-created_at')[:5]
    
    # Calculate SLA information
    severity_sla = {
        'Critical': 7,
        'High': 30,
        'Medium': 90,
        'Low': 180
    }
    
    sla_days = severity_sla.get(vulnerability.severity, 90)
    days_open = (timezone.now().date() - vulnerability.created_at.date()).days
    is_overdue = vulnerability.status == 'Open' and days_open > sla_days
    days_until_sla = max(0, sla_days - days_open) if vulnerability.status == 'Open' else 0
    
    context = {
        'vulnerability': vulnerability,
        'related_vulnerabilities': related_vulnerabilities,
        'sla_days': sla_days,
        'days_open': days_open,
        'is_overdue': is_overdue,
        'days_until_sla': days_until_sla,
        'can_edit': (
            request.user == vulnerability.created_by or 
            request.user.is_superuser or 
            request.user.user_type == 'M'
        )
    }
    
    return render(request, "CalendarinhoApp/vulnerability_detail.html", context)


@login_required
def vulnerability_analytics(request):
    """Vulnerability analytics dashboard"""
    # Support client filter via query string (?client_ids=1,2)
    raw_client_ids = request.GET.get('client_ids')
    client_ids = None
    if raw_client_ids:
        client_ids = [cid.strip() for cid in raw_client_ids.split(',') if cid.strip()]
    analytics_data = get_vulnerability_analytics(client_ids)
    
    # If this is an AJAX request, return JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
    
    context = {
        'analytics': analytics_data,
        'selected_client_ids': ','.join(client_ids) if client_ids else ''
    }
    
    return render(request, "CalendarinhoApp/vulnerability_analytics.html", context)


@login_required
def vulnerability_statistics(request):
    """New consolidated statistics page with client filter, cards, charts, and table"""
    # Pass-through selected clients for initial render (JS will fetch data)
    raw_client_ids = request.GET.get('client_ids')
    selected_client_ids = ''
    if raw_client_ids:
        selected_client_ids = ','.join([cid.strip() for cid in raw_client_ids.split(',') if cid.strip()])
    context = {
        'selected_client_ids': selected_client_ids
    }
    return render(request, "CalendarinhoApp/vulnerability_statistics.html", context)


@login_required
def engagement_vulnerabilities(request, eng_id):
    """View vulnerabilities for a specific engagement with filtering"""
    engagement = get_object_or_404(Engagement, id=eng_id)
    
    # Check if user can view this engagement
    if not (request.user in engagement.employees.all() or 
            request.user.is_superuser or request.user.user_type == 'M'):
        return not_found(request)
    
    # Get vulnerabilities for this engagement
    vulnerabilities = engagement.vulnerabilities.select_related('created_by', 'fixed_by').all()
    
    # Apply filters if provided
    filter_form = VulnerabilityFilterForm(request.GET or None)
    if filter_form.is_valid():
        filters = {k: v for k, v in filter_form.cleaned_data.items() if v is not None and v != ''}
        
        if filters.get('search'):
            search_term = filters['search']
            vulnerabilities = vulnerabilities.filter(
                Q(title__icontains=search_term) | 
                Q(description__icontains=search_term)
            )
        
        if filters.get('severity'):
            vulnerabilities = vulnerabilities.filter(severity=filters['severity'])
        
        if filters.get('status'):
            vulnerabilities = vulnerabilities.filter(status=filters['status'])
        
        if filters.get('created_by'):
            vulnerabilities = vulnerabilities.filter(created_by=filters['created_by'])
        
        # Date filters
        if filters.get('created_from'):
            vulnerabilities = vulnerabilities.filter(created_at__date__gte=filters['created_from'])
        
        if filters.get('created_to'):
            vulnerabilities = vulnerabilities.filter(created_at__date__lte=filters['created_to'])
    
    # Sort vulnerabilities by severity priority
    severity_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
    vulnerabilities = sorted(
        vulnerabilities,
        key=lambda v: (severity_order.get(v.severity, 5), v.created_at)
    )
    
    # If this is an AJAX request for filtered data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        vulnerabilities_data = []
        for vuln in vulnerabilities:
            vulnerabilities_data.append({
                'id': vuln.id,
                'title': vuln.title,
                'description': vuln.description[:100] + '...' if len(vuln.description) > 100 else vuln.description,
                'severity': vuln.severity,
                'status': vuln.status,
                'created_by_name': vuln.created_by.get_full_name(),
                'created_at': vuln.created_at.isoformat(),
                'fixed_at': vuln.fixed_at.isoformat() if vuln.fixed_at else None,
                'fixed_by_name': vuln.fixed_by.get_full_name() if vuln.fixed_by else None,
                'severity_color': vuln.get_severity_color(),
                'severity_icon': vuln.get_severity_icon(),
                'is_overdue': vuln.is_overdue(),
                'days_to_fix': vuln.days_to_fix(),
            })
        
        return JsonResponse({
            'success': True,
            'vulnerabilities': vulnerabilities_data,
            'engagement': {
                'id': engagement.id,
                'name': engagement.name,
                'client_name': engagement.client.name
            }
        })
    
    # Summary statistics for this engagement
    vulnerability_summary = engagement.get_vulnerability_summary()
    
    context = {
        'engagement': engagement,
        'vulnerabilities': vulnerabilities,
        'vulnerability_summary': vulnerability_summary,
        'filter_form': filter_form,
        'bulk_form': BulkActionForm(),
    }
    
    return render(request, "CalendarinhoApp/engagement_vulnerabilities.html", context)


@login_required
def client_vulnerabilities(request, cli_id):
    """View vulnerabilities for a specific client across all engagements"""
    client = get_object_or_404(Client, id=cli_id)
    
    # Get all vulnerabilities for this client's engagements
    vulnerabilities = Vulnerability.objects.filter(
        engagement__client=client
    ).select_related('engagement', 'created_by', 'fixed_by').all()
    
    # Apply filters if provided
    filter_form = VulnerabilityFilterForm(request.GET or None)
    if filter_form.is_valid():
        filters = {k: v for k, v in filter_form.cleaned_data.items() if v is not None and v != ''}
        
        if filters.get('search'):
            search_term = filters['search']
            vulnerabilities = vulnerabilities.filter(
                Q(title__icontains=search_term) | 
                Q(description__icontains=search_term)
            )
        
        if filters.get('severity'):
            vulnerabilities = vulnerabilities.filter(severity=filters['severity'])
        
        if filters.get('status'):
            vulnerabilities = vulnerabilities.filter(status=filters['status'])
        
        if filters.get('engagement'):
            vulnerabilities = vulnerabilities.filter(engagement=filters['engagement'])
    
    # Group vulnerabilities by engagement
    engagement_vulnerabilities = {}
    for vuln in vulnerabilities:
        eng_id = vuln.engagement.id
        if eng_id not in engagement_vulnerabilities:
            engagement_vulnerabilities[eng_id] = {
                'engagement': vuln.engagement,
                'vulnerabilities': []
            }
        engagement_vulnerabilities[eng_id]['vulnerabilities'].append(vuln)
    
    # If this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = []
        for eng_data in engagement_vulnerabilities.values():
            eng_vulns = []
            for vuln in eng_data['vulnerabilities']:
                eng_vulns.append({
                    'id': vuln.id,
                    'title': vuln.title,
                    'severity': vuln.severity,
                    'status': vuln.status,
                    'created_at': vuln.created_at.isoformat(),
                    'is_overdue': vuln.is_overdue(),
                })
            
            response_data.append({
                'engagement': {
                    'id': eng_data['engagement'].id,
                    'name': eng_data['engagement'].name
                },
                'vulnerabilities': eng_vulns
            })
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'client': {
                'id': client.id,
                'name': client.name
            }
        })
    
    # Summary statistics for this client
    vulnerability_summary = client.get_vulnerability_summary()
    
    context = {
        'client': client,
        'engagement_vulnerabilities': engagement_vulnerabilities,
        'vulnerability_summary': vulnerability_summary,
        'filter_form': filter_form,
        'total_vulnerabilities': vulnerabilities.count(),
    }
    
    return render(request, "CalendarinhoApp/client_vulnerabilities.html", context)


def get_vulnerability_export_data(vulnerability_ids):
    """Get vulnerability data formatted for export"""
    vulnerabilities = Vulnerability.objects.filter(
        id__in=vulnerability_ids
    ).select_related('engagement__client', 'created_by', 'fixed_by')
    
    export_data = []
    for vuln in vulnerabilities:
        export_data.append({
            'ID': vuln.id,
            'Title': vuln.title,
            'Description': vuln.description,
            'Severity': vuln.severity,
            'Status': vuln.status,
            'Engagement': vuln.engagement.name,
            'Client': vuln.engagement.client.name,
            'Created By': vuln.created_by.get_full_name(),
            'Created Date': vuln.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Fixed Date': vuln.fixed_at.strftime('%Y-%m-%d %H:%M:%S') if vuln.fixed_at else '',
            'Fixed By': vuln.fixed_by.get_full_name() if vuln.fixed_by else '',
            'Days to Fix': vuln.days_to_fix() if vuln.days_to_fix() else '',
            'Is Overdue': 'Yes' if vuln.is_overdue() else 'No',
        })
    
    return export_data


@login_required
def export_vulnerabilities(request):
    """Export vulnerabilities to CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get vulnerability IDs from request
    vulnerability_ids = request.GET.getlist('ids')
    if not vulnerability_ids:
        return JsonResponse({
            'success': False,
            'error': 'No vulnerabilities selected for export'
        }, status=400)
    
    # Get export data
    export_data = get_vulnerability_export_data(vulnerability_ids)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vulnerabilities_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    if export_data:
        writer = csv.DictWriter(response, fieldnames=export_data[0].keys())
        writer.writeheader()
        writer.writerows(export_data)
    
    return response