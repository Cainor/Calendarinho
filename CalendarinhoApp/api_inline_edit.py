"""
Inline editing API endpoints for seamless field updates
Provides RESTful PATCH endpoints for updating individual fields with proper validation
"""

import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from .models import Vulnerability, Engagement, Report, Leave, Client, Comment, Service
from .forms import (
    InlineEditVulnerabilityForm, 
    InlineEditEngagementForm,
    InlineEditReportForm,
    InlineEditLeaveForm,
    InlineEditClientForm
)
from users.models import CustomUser as Employee

logger = logging.getLogger(__name__)


def create_inline_edit_response(success=True, message="", data=None, errors=None):
    """Standardized JSON response for inline editing operations"""
    response_data = {
        'success': success,
        'message': message,
        'timestamp': timezone.now().isoformat()
    }
    
    if data:
        response_data['data'] = data
    
    if errors:
        response_data['errors'] = errors
    
    return JsonResponse(response_data, status=200 if success else 400)


def check_edit_permissions(request, obj, field_name=None):
    """
    Check if user has permission to edit the given object/field
    Returns (has_permission: bool, error_message: str)
    """
    if not request.user.is_authenticated:
        return False, "Authentication required"
    
    # Superusers and managers can edit everything
    if request.user.is_superuser or request.user.user_type == 'M':
        return True, ""
    
    # Object-specific permission checks
    if isinstance(obj, Vulnerability):
        # Only creator or engagement members can edit vulnerabilities
        if (request.user == obj.created_by or 
            request.user in obj.engagement.employees.all()):
            return True, ""
        return False, "You don't have permission to edit this vulnerability"
    
    elif isinstance(obj, Engagement):
        # Only engagement members can edit engagements
        if request.user in obj.employees.all():
            return True, ""
        return False, "You don't have permission to edit this engagement"
    
    elif isinstance(obj, Report):
        # Only creator or engagement members can edit reports
        if (request.user == obj.user or 
            request.user in obj.engagement.employees.all()):
            return True, ""
        return False, "You don't have permission to edit this report"
    
    elif isinstance(obj, Leave):
        # Only leave owner can edit their own leave
        if request.user == obj.employee:
            return True, ""
        return False, "You can only edit your own leave requests"
    
    elif isinstance(obj, Client):
        # Only managers and superusers can edit clients (already checked above)
        return False, "You don't have permission to edit client information"
    
    elif isinstance(obj, Comment):
        # Only comment author can edit their comments
        if request.user == obj.user:
            return True, ""
        return False, "You can only edit your own comments"
    
    return False, "Permission denied"


# Vulnerability inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_vulnerability_field(request, vuln_id):
    """Update a single field of a vulnerability"""
    try:
        vulnerability = get_object_or_404(Vulnerability, id=vuln_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, vulnerability)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        # Ensure field_value preserves spaces if it's a string
        if isinstance(field_value, str):
            field_value = field_value  # Keep original spaces - no additional processing
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['title', 'description', 'severity', 'status']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Create form with single field data
        form_data = {field_name: field_value}
        form = InlineEditVulnerabilityForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                # Update the field
                setattr(vulnerability, field_name, form.cleaned_data[field_name])
                
                # Handle status changes
                if field_name == 'status':
                    if form.cleaned_data[field_name] == 'Fixed':
                        vulnerability.fixed_at = timezone.now()
                        vulnerability.fixed_by = request.user
                    else:
                        vulnerability.fixed_at = None
                        vulnerability.fixed_by = None
                
                vulnerability.save()
                
                # Prepare response data
                response_data = {
                    'id': vulnerability.id,
                    'field': field_name,
                    'value': getattr(vulnerability, field_name),
                    'formatted_value': str(getattr(vulnerability, field_name)),
                }
                
                # Add extra context for status changes
                if field_name == 'status':
                    response_data.update({
                        'fixed_at': vulnerability.fixed_at.isoformat() if vulnerability.fixed_at else None,
                        'fixed_by': vulnerability.fixed_by.get_full_name() if vulnerability.fixed_by else None,
                        'status_color': vulnerability.get_severity_color(),
                    })
                
                logger.info(f"User {request.user.username} updated vulnerability {vuln_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating vulnerability {vuln_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Engagement inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_engagement_field(request, eng_id):
    """Update a single field of an engagement"""
    try:
        engagement = get_object_or_404(Engagement, id=eng_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, engagement)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        # Ensure field_value preserves spaces if it's a string
        if isinstance(field_value, str):
            # Keep original spaces - no stripping or additional processing
            pass
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['name', 'start_date', 'end_date', 'scope', 'service_type']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Special handling for service_type field - validate service exists but keep as ID for form
        if field_name == 'service_type':
            if isinstance(field_value, (int, str)) and str(field_value).isdigit():
                try:
                    service_id = int(field_value)
                    # Just validate the service exists, but keep the ID for the form
                    service = Service.objects.get(id=service_id)
                    # Keep field_value as string ID for the form
                    field_value = str(service_id)
                except Service.DoesNotExist:
                    return create_inline_edit_response(False, "Invalid service selected")
                except Exception as e:
                    logger.error(f"Error during service validation: {str(e)}")
                    return create_inline_edit_response(False, f"Error validating service: {str(e)}")
            else:
                return create_inline_edit_response(False, "Service ID must be a valid number")
        
        # Create form with single field data
        form_data = {field_name: field_value}
        form = InlineEditEngagementForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                setattr(engagement, field_name, form.cleaned_data[field_name])
                engagement.save()
                
                # Get the actual saved value for response
                saved_value = getattr(engagement, field_name)
                
                # Handle different field types for JSON serialization
                if field_name == 'service_type' and hasattr(saved_value, 'id'):
                    # For service_type, return service details instead of the object
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value.id,  # Return the ID, not the object
                        'formatted_value': f"{saved_value.name} ({saved_value.short_name})",
                        'service_id': saved_value.id,
                        'service_name': saved_value.name,
                        'service_short_name': saved_value.short_name,
                    }
                elif field_name in ['start_date', 'end_date']:
                    # For dates, handle special formatting
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value.strftime('%Y-%m-%d') if saved_value else "",
                        'formatted_value': saved_value.strftime('%Y-%m-%d') if saved_value else "",
                    }
                else:
                    # For regular fields
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value,
                        'formatted_value': str(saved_value),
                    }
                
                logger.info(f"User {request.user.username} updated engagement {eng_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating engagement {eng_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Report inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_report_field(request, report_id):
    """Update a single field of a report"""
    try:
        report = get_object_or_404(Report, id=report_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, report)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        # Ensure field_value preserves spaces if it's a string
        if isinstance(field_value, str):
            # Keep original spaces - no stripping or additional processing
            pass
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['note', 'report_type']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Create form with single field data
        form_data = {field_name: field_value}
        form = InlineEditReportForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                setattr(report, field_name, form.cleaned_data[field_name])
                report.save()
                
                response_data = {
                    'id': report.id,
                    'field': field_name,
                    'value': getattr(report, field_name),
                    'formatted_value': str(getattr(report, field_name)),
                }
                
                logger.info(f"User {request.user.username} updated report {report_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating report {report_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Leave inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_leave_field(request, leave_id):
    """Update a single field of a leave request"""
    try:
        leave = get_object_or_404(Leave, id=leave_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, leave)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        # Ensure field_value preserves spaces if it's a string
        if isinstance(field_value, str):
            # Keep original spaces - no stripping or additional processing
            pass
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['note', 'start_date', 'end_date', 'leave_type']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Create form with single field data
        form_data = {field_name: field_value}
        form = InlineEditLeaveForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                setattr(leave, field_name, form.cleaned_data[field_name])
                leave.save()
                
                response_data = {
                    'id': leave.id,
                    'field': field_name,
                    'value': getattr(leave, field_name),
                    'formatted_value': str(getattr(leave, field_name)),
                }
                
                # Add formatted date display
                if field_name in ['start_date', 'end_date']:
                    date_value = getattr(leave, field_name)
                    response_data['formatted_value'] = date_value.strftime('%Y-%m-%d') if date_value else ""
                
                logger.info(f"User {request.user.username} updated leave {leave_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating leave {leave_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Client inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_client_field(request, client_id):
    """Update a single field of a client"""
    try:
        client = get_object_or_404(Client, id=client_id)
        
        # Check permissions (only managers and superusers)
        has_permission, error_msg = check_edit_permissions(request, client)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        # Ensure field_value preserves spaces if it's a string
        if isinstance(field_value, str):
            # Keep original spaces - no stripping or additional processing
            pass
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['name', 'acronym', 'code']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Create form with single field data
        form_data = {field_name: field_value}
        form = InlineEditClientForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                setattr(client, field_name, form.cleaned_data[field_name])
                client.save()
                
                response_data = {
                    'id': client.id,
                    'field': field_name,
                    'value': getattr(client, field_name),
                    'formatted_value': str(getattr(client, field_name)),
                }
                
                logger.info(f"User {request.user.username} updated client {client_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating client {client_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Comment inline editing endpoints

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def update_comment_field(request, comment_id):
    """Update a comment's body text"""
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, comment)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Only body field is editable for comments
        if field_name != 'body':
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Validate comment body but preserve internal spaces
        if not field_value or len(field_value.strip()) < 3:
            return create_inline_edit_response(False, "Comment must be at least 3 characters long")
        
        with transaction.atomic():
            # Preserve internal spaces but trim leading/trailing whitespace
            comment.body = field_value.strip()
            comment.save()
            
            response_data = {
                'id': comment.id,
                'field': field_name,
                'value': comment.body,
                'formatted_value': comment.body,
                'updated_at': timezone.now().isoformat(),
            }
            
            logger.info(f"User {request.user.username} updated comment {comment_id}")
            return create_inline_edit_response(True, "Comment updated successfully", response_data)
    
    except Exception as e:
        logger.error(f"Error updating comment {comment_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the comment")


# Batch update endpoints for efficiency

@login_required
@csrf_protect
@require_http_methods(["POST", "PATCH"])
def batch_update_vulnerabilities(request):
    """Batch update multiple vulnerabilities"""
    try:
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        updates = data.get('updates', [])
        if not updates:
            return create_inline_edit_response(False, "No updates provided")
        
        results = []
        errors = []
        
        with transaction.atomic():
            for update_data in updates:
                vuln_id = update_data.get('id')
                field_name = update_data.get('field')
                field_value = update_data.get('value')
                
                try:
                    vulnerability = get_object_or_404(Vulnerability, id=vuln_id)
                    
                    # Check permissions
                    has_permission, error_msg = check_edit_permissions(request, vulnerability)
                    if not has_permission:
                        errors.append({'id': vuln_id, 'error': error_msg})
                        continue
                    
                    # Validate and update
                    editable_fields = ['title', 'description', 'severity', 'status']
                    if field_name not in editable_fields:
                        errors.append({'id': vuln_id, 'error': f"Field '{field_name}' is not editable"})
                        continue
                    
                    form_data = {field_name: field_value}
                    form = InlineEditVulnerabilityForm(data=form_data)
                    
                    if form.is_valid():
                        setattr(vulnerability, field_name, form.cleaned_data[field_name])
                        
                        if field_name == 'status':
                            if form.cleaned_data[field_name] == 'Fixed':
                                vulnerability.fixed_at = timezone.now()
                                vulnerability.fixed_by = request.user
                            else:
                                vulnerability.fixed_at = None
                                vulnerability.fixed_by = None
                        
                        vulnerability.save()
                        results.append({'id': vuln_id, 'success': True})
                    else:
                        errors.append({'id': vuln_id, 'error': form.errors})
                
                except Exception as e:
                    errors.append({'id': vuln_id, 'error': str(e)})
        
        response_data = {
            'updated_count': len(results),
            'error_count': len(errors),
            'results': results,
            'errors': errors
        }
        
        success = len(errors) == 0
        message = f"Updated {len(results)} vulnerabilities" + (f", {len(errors)} errors" if errors else "")
        
        return create_inline_edit_response(success, message, response_data)
    
    except Exception as e:
        logger.error(f"Error in batch update: {str(e)}")
        return create_inline_edit_response(False, "An error occurred during batch update")


# API Documentation endpoint

@login_required
def inline_edit_api_docs(request):
    """Return API documentation for inline editing endpoints"""
    from .inline_edit_docs import get_api_documentation, get_usage_examples
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'documentation': get_api_documentation(),
            'examples': get_usage_examples()
        })
    
    # Return HTML documentation page
    from django.shortcuts import render
    context = {
        'documentation': get_api_documentation(),
        'examples': get_usage_examples()
    }
    return render(request, 'CalendarinhoApp/inline_edit_docs.html', context)


# Services API endpoint for dynamic dropdown population

@login_required
@require_http_methods(["GET"])
def get_services(request):
    """Get all available services for dropdown population"""
    try:
        services = Service.objects.all().order_by('name')
        services_data = []
        
        for service in services:
            services_data.append({
                'id': service.id,
                'name': service.name,
                'short_name': service.short_name,
                'display_name': f"{service.name} ({service.short_name})"
            })
        
        return create_inline_edit_response(
            True, 
            f"Found {len(services_data)} services",
            {'services': services_data}
        )
    
    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}")
        return create_inline_edit_response(False, "Error retrieving services")


# Employee Management API endpoints for engagement inline editing

@login_required
@require_http_methods(["GET"])
def get_engagement_employees(request, eng_id):
    """Get current employees assigned to an engagement"""
    try:
        engagement = get_object_or_404(Engagement, id=eng_id)
        
        # Check permissions - only engagement members and managers can view
        has_permission, error_msg = check_edit_permissions(request, engagement)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        current_employees = engagement.employees.filter(is_active=True).order_by('first_name', 'last_name')
        employees_data = []
        
        for employee in current_employees:
            employees_data.append({
                'id': employee.id,
                'username': employee.username,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'full_name': employee.get_full_name(),
                'user_type': employee.get_user_type_display(),
                'email': employee.email
            })
        
        return create_inline_edit_response(
            True,
            f"Found {len(employees_data)} employees in engagement",
            {
                'engagement_id': engagement.id,
                'engagement_name': engagement.name,
                'employees': employees_data
            }
        )
    
    except Exception as e:
        logger.error(f"Error fetching engagement {eng_id} employees: {str(e)}")
        return create_inline_edit_response(False, "Error retrieving engagement employees")


def calculate_employee_availability(employee, engagement_start, engagement_end):
    """Calculate employee availability for a specific engagement period using Team Finder logic"""
    from datetime import timedelta
    
    # Calculate total days in the engagement period
    total_days = (engagement_end - engagement_start).days + 1
    
    # Calculate busy days using the same logic as Team Finder
    busy_days = set()
    
    # Get all engagements for the employee in the date range
    engagements = Engagement.objects.filter(
        employees=employee,
        start_date__lte=engagement_end,
        end_date__gte=engagement_start
    )
    
    # Get all leaves for the employee in the date range
    from .models import Leave
    leaves = Leave.objects.filter(
        employee_id=employee.id,
        start_date__lte=engagement_end,
        end_date__gte=engagement_start
    )
    
    # Add engagement days to busy_days set
    for eng in engagements:
        eng_start = max(engagement_start, eng.start_date)
        eng_end = min(engagement_end, eng.end_date)
        current_date = eng_start
        while current_date <= eng_end:
            busy_days.add(current_date)
            current_date += timedelta(days=1)
    
    # Add leave days to busy_days set
    for leave in leaves:
        leave_start = max(engagement_start, leave.start_date)
        leave_end = min(engagement_end, leave.end_date)
        current_date = leave_start
        while current_date <= leave_end:
            busy_days.add(current_date)
            current_date += timedelta(days=1)
    
    busy_days_count = len(busy_days)
    availability_percentage = int(((total_days - busy_days_count) / total_days) * 100) if total_days > 0 else 100
    
    return {
        'total_days': total_days,
        'busy_days': busy_days_count,
        'available_days': total_days - busy_days_count,
        'availability_percentage': availability_percentage,
        'is_completely_available': busy_days_count == 0,
        'is_partially_available': 0 < busy_days_count < total_days,
        'is_completely_busy': busy_days_count >= total_days
    }


@login_required
@require_http_methods(["GET"])
def get_available_employees(request):
    """Get all available employees for adding to engagements with availability info"""
    try:
        # Only managers and superusers can see all employees
        if not (request.user.is_superuser or request.user.user_type == 'M'):
            return create_inline_edit_response(False, "Permission denied")
        
        # Get engagement ID and dates for availability calculation
        engagement_id = request.GET.get('engagement_id')
        engagement_start = None
        engagement_end = None
        
        if engagement_id:
            try:
                engagement = get_object_or_404(Engagement, id=engagement_id)
                engagement_start = engagement.start_date
                engagement_end = engagement.end_date
            except:
                pass  # Continue without availability calculation
        
        # Get active employees, excluding the current user if desired
        employees = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        employees_data = []
        
        for employee in employees:
            status_info = employee.get_status_display()
            
            # Get current engagements for display
            current_engagements = Engagement.objects.filter(
                employees=employee,
                end_date__gte=timezone.now().date()
            ).values_list('name', flat=True)
            
            # Calculate availability for the specific engagement period
            availability_info = None
            if engagement_start and engagement_end:
                availability_info = calculate_employee_availability(employee, engagement_start, engagement_end)
            
            employee_data = {
                'id': employee.id,
                'username': employee.username,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'full_name': employee.get_full_name(),
                'user_type': employee.get_user_type_display(),
                'email': employee.email,
                'status': status_info.get('type', 'Available'),
                'status_label': status_info.get('label', 'Available'),
                'status_class': status_info.get('class', 'success'),
                'current_engagements': list(current_engagements),
                'engagement_count': len(current_engagements)
            }
            
            # Add availability information if calculated
            if availability_info:
                employee_data.update({
                    'availability': availability_info,
                    'availability_text': f"{availability_info['availability_percentage']}% available",
                    'busy_days_text': f"{availability_info['busy_days']}/{availability_info['total_days']} days busy"
                })
            
            employees_data.append(employee_data)
        
        return create_inline_edit_response(
            True,
            f"Found {len(employees_data)} available employees",
            {'employees': employees_data}
        )
    
    except Exception as e:
        logger.error(f"Error fetching available employees: {str(e)}")
        return create_inline_edit_response(False, "Error retrieving available employees")


@login_required
@csrf_protect
@require_http_methods(["POST"])
def add_employee_to_engagement(request, eng_id):
    """Add an employee to an engagement"""
    try:
        engagement = get_object_or_404(Engagement, id=eng_id)
        
        # Check permissions - only managers and superusers can modify engagement teams
        if not (request.user.is_superuser or request.user.user_type == 'M'):
            return create_inline_edit_response(False, "Only managers can modify engagement teams")
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        employee_id = data.get('employee_id')
        if not employee_id:
            return create_inline_edit_response(False, "Employee ID is required")
        
        try:
            employee = get_object_or_404(Employee, id=employee_id, is_active=True)
        except:
            return create_inline_edit_response(False, "Employee not found or inactive")
        
        # Check if employee is already assigned
        if engagement.employees.filter(id=employee_id).exists():
            return create_inline_edit_response(False, "Employee is already assigned to this engagement")
        
        # Note: We no longer block based on conflicts - let managers decide
        # Just log if there are overlapping engagements for awareness
        has_conflict = employee.overlapCheck(engagement.start_date, engagement.end_date)
        conflict_info = ""
        if has_conflict:
            try:
                conflict_details = employee.get_availability_status(engagement.start_date)
                conflict_info = f" (Note: Employee has existing commitment: {conflict_details['status']})"
            except:
                conflict_info = " (Note: Employee has scheduling overlap with existing engagements)"
        
        # Add employee to engagement
        with transaction.atomic():
            engagement.employees.add(employee)
            
            response_data = {
                'engagement_id': engagement.id,
                'employee_id': employee.id,
                'employee_name': employee.get_full_name(),
                'total_employees': engagement.employees.count()
            }
            
            logger.info(f"User {request.user.username} added employee {employee.get_full_name()} to engagement {engagement.name}{conflict_info}")
            return create_inline_edit_response(True, f"Employee added to engagement successfully{conflict_info}", response_data)
    
    except Exception as e:
        logger.error(f"Error adding employee to engagement {eng_id}: {str(e)}")
        return create_inline_edit_response(False, "Error adding employee to engagement")


@login_required
@csrf_protect
@require_http_methods(["POST", "DELETE"])
def remove_employee_from_engagement(request, eng_id):
    """Remove an employee from an engagement"""
    try:
        engagement = get_object_or_404(Engagement, id=eng_id)
        
        # Check permissions - only managers and superusers can modify engagement teams
        if not (request.user.is_superuser or request.user.user_type == 'M'):
            return create_inline_edit_response(False, "Only managers can modify engagement teams")
        
        # Parse request data with enhanced space handling
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        employee_id = data.get('employee_id')
        if not employee_id:
            return create_inline_edit_response(False, "Employee ID is required")
        
        try:
            employee = get_object_or_404(Employee, id=employee_id)
        except:
            return create_inline_edit_response(False, "Employee not found")
        
        # Check if employee is currently assigned
        if not engagement.employees.filter(id=employee_id).exists():
            return create_inline_edit_response(False, "Employee is not assigned to this engagement")
        
        # Note: We allow removing all employees - managers decide what's appropriate
        
        # Remove employee from engagement
        with transaction.atomic():
            engagement.employees.remove(employee)
            
            response_data = {
                'engagement_id': engagement.id,
                'employee_id': employee.id,
                'employee_name': employee.get_full_name(),
                'total_employees': engagement.employees.count()
            }
            
            logger.info(f"User {request.user.username} removed employee {employee.get_full_name()} from engagement {engagement.name}")
            return create_inline_edit_response(True, "Employee removed from engagement successfully", response_data)
    
    except Exception as e:
        logger.error(f"Error removing employee from engagement {eng_id}: {str(e)}")
        return create_inline_edit_response(False, "Error removing employee from engagement")


# Enhanced JSON processing for better space character handling

def parse_json_with_preserved_spaces(request):
    """
    Enhanced JSON parser that properly handles spaces and special characters
    This addresses the space character issue in inline editing
    """
    try:
        # Decode the request body with proper encoding handling
        body = request.body
        if isinstance(body, bytes):
            # Try UTF-8 first, fallback to latin-1 if needed
            try:
                decoded_body = body.decode('utf-8')
            except UnicodeDecodeError:
                decoded_body = body.decode('latin-1')
        else:
            decoded_body = body
        
        # Parse JSON with preserved whitespace
        data = json.loads(decoded_body)
        
        # Ensure string values preserve their original spacing
        def preserve_spaces(obj):
            if isinstance(obj, dict):
                return {k: preserve_spaces(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [preserve_spaces(item) for item in obj]
            elif isinstance(obj, str):
                # Return the string as-is, preserving all spaces
                return obj
            else:
                return obj
        
        return preserve_spaces(data), None
    
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {str(e)}"
    except UnicodeDecodeError as e:
        return None, f"Encoding error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# Enhanced inline edit endpoint with better space handling

@login_required
@csrf_protect 
@require_http_methods(["POST", "PATCH"])
def update_engagement_field_enhanced(request, eng_id):
    """Enhanced engagement field update with better space character handling"""
    try:
        engagement = get_object_or_404(Engagement, id=eng_id)
        
        # Check permissions
        has_permission, error_msg = check_edit_permissions(request, engagement)
        if not has_permission:
            return create_inline_edit_response(False, error_msg)
        
        # Use enhanced JSON parsing to preserve spaces
        data, error = parse_json_with_preserved_spaces(request)
        if error:
            return create_inline_edit_response(False, f"JSON parsing error: {error}")
        
        field_name = data.get('field')
        field_value = data.get('value')
        
        if not field_name:
            return create_inline_edit_response(False, "Field name is required")
        
        # Validate field exists and is editable
        editable_fields = ['name', 'start_date', 'end_date', 'scope', 'service_type']
        if field_name not in editable_fields:
            return create_inline_edit_response(False, f"Field '{field_name}' is not editable")
        
        # Special handling for service_type field - validate service exists but keep as ID for form
        if field_name == 'service_type':
            if isinstance(field_value, (int, str)) and str(field_value).isdigit():
                try:
                    service_id = int(field_value)
                    # Just validate the service exists, but keep the ID for the form
                    service = Service.objects.get(id=service_id)
                    # Keep field_value as string ID for the form
                    field_value = str(service_id)
                except Service.DoesNotExist:
                    return create_inline_edit_response(False, "Invalid service selected")
            else:
                return create_inline_edit_response(False, "Service ID must be a valid number")
        
        # Create form with single field data, preserving original spacing
        form_data = {field_name: field_value}
        form = InlineEditEngagementForm(data=form_data)
        
        if form.is_valid():
            with transaction.atomic():
                setattr(engagement, field_name, form.cleaned_data[field_name])
                engagement.save()
                
                # Get the actual saved value for response
                saved_value = getattr(engagement, field_name)
                
                # Handle different field types for JSON serialization
                if field_name == 'service_type' and hasattr(saved_value, 'id'):
                    # For service_type, return service details instead of the object
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value.id,  # Return the ID, not the object
                        'formatted_value': f"{saved_value.name} ({saved_value.short_name})",
                        'service_id': saved_value.id,
                        'service_name': saved_value.name,
                        'service_short_name': saved_value.short_name,
                    }
                elif field_name in ['start_date', 'end_date']:
                    # For dates, handle special formatting
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value.strftime('%Y-%m-%d') if saved_value else "",
                        'formatted_value': saved_value.strftime('%Y-%m-%d') if saved_value else "",
                    }
                else:
                    # For regular fields
                    response_data = {
                        'id': engagement.id,
                        'field': field_name,
                        'value': saved_value,
                        'formatted_value': str(saved_value),
                    }
                
                logger.info(f"User {request.user.username} updated engagement {eng_id} field '{field_name}' to '{field_value}'")
                return create_inline_edit_response(True, "Field updated successfully", response_data)
        
        else:
            return create_inline_edit_response(False, "Validation failed", errors=form.errors)
    
    except Exception as e:
        logger.error(f"Error updating engagement {eng_id}: {str(e)}")
        return create_inline_edit_response(False, "An error occurred while updating the field")


# Test endpoint for inline editing functionality

@login_required
def inline_edit_test(request):
    """Test endpoint for inline editing functionality"""
    if not (request.user.is_superuser or request.user.user_type == 'M'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get sample data for testing
    from .models import Vulnerability, Engagement, Report
    
    sample_vulnerabilities = Vulnerability.objects.select_related('engagement__client', 'created_by')[:5]
    sample_engagements = Engagement.objects.select_related('client')[:5] 
    sample_reports = Report.objects.select_related('engagement')[:5]
    
    context = {
        'vulnerabilities': sample_vulnerabilities,
        'engagements': sample_engagements,
        'reports': sample_reports,
    }
    
    return render(request, 'CalendarinhoApp/inline_edit_test.html', context)