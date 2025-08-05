"""
API Documentation Module for Phase 2 Backend Features

This module provides comprehensive documentation for all the new API endpoints
created for Phase 2 backend enhancements.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse


@login_required
def api_documentation(request):
    """API documentation endpoint"""
    
    # Check if JSON response is requested
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(get_api_documentation_data())
    
    # Otherwise return HTML documentation page
    context = {
        'api_docs': get_api_documentation_data(),
        'title': 'Phase 2 API Documentation'
    }
    return TemplateResponse(request, 'CalendarinhoApp/api_documentation.html', context)


def get_api_documentation_data():
    """Get comprehensive API documentation data"""
    
    return {
        'title': 'Calendarinho Phase 2 API Documentation',
        'version': '2.0',
        'description': 'Enhanced API endpoints with advanced filtering, bulk operations, and mobile optimization',
        'base_url': '/api/',
        'categories': [
            {
                'name': 'Advanced Filtering APIs',
                'description': 'Enhanced filtering capabilities for all data types',
                'endpoints': [
                    {
                        'name': 'Filtered Employees',
                        'method': 'GET',
                        'url': '/api/employees/filtered/',
                        'description': 'Get employees with advanced filtering options',
                        'parameters': [
                            {
                                'name': 'search',
                                'type': 'string',
                                'required': False,
                                'description': 'Search by name'
                            },
                            {
                                'name': 'status',
                                'type': 'string',
                                'required': False,
                                'description': 'Filter by status (Available, Engaged, Training, Vacation)',
                                'options': ['Available', 'Engaged', 'Training', 'Vacation']
                            }
                        ]
                    }
                ]
            }
        ]
    }


@login_required
def api_documentation(request):
    """Provide API documentation"""
    return JsonResponse(API_DOCUMENTATION)