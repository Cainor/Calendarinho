"""
Inline Editing API Documentation and Examples
Provides comprehensive documentation for the inline editing backend infrastructure
"""

API_DOCUMENTATION = {
    "title": "Calendarinho Inline Editing API",
    "version": "1.0",
    "description": "RESTful API endpoints for seamless inline field editing",
    "base_url": "/api/",
    
    "authentication": {
        "type": "Session-based authentication with CSRF protection",
        "required_headers": {
            "X-CSRFToken": "CSRF token from cookie or meta tag",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
    },
    
    "endpoints": {
        "vulnerability": {
            "url": "/api/vulnerability/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a single field of a vulnerability",
            "permissions": "Creator, engagement members, managers, or superusers",
            "editable_fields": ["title", "description", "severity", "status"],
            "request_format": {
                "field": "string (field name)",
                "value": "mixed (new field value)"
            },
            "example_request": {
                "field": "severity",
                "value": "High"
            },
            "example_response": {
                "success": True,
                "message": "Field updated successfully",
                "data": {
                    "id": 123,
                    "field": "severity",
                    "value": "High",
                    "formatted_value": "High"
                },
                "timestamp": "2023-12-01T10:30:00Z"
            },
            "validation_rules": {
                "title": "Minimum 3 characters, maximum 200 characters",
                "description": "Minimum 10 characters",
                "severity": "Must be one of: Critical, High, Medium, Low",
                "status": "Must be one of: Open, Fixed"
            }
        },
        
        "engagement": {
            "url": "/api/engagement/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a single field of an engagement",
            "permissions": "Engagement members, managers, or superusers",
            "editable_fields": ["name", "start_date", "end_date", "scope"],
            "note": "Regular team members can only edit 'scope' field",
            "request_format": {
                "field": "string (field name)",
                "value": "mixed (new field value)"
            },
            "example_request": {
                "field": "name",
                "value": "Updated Engagement Name"
            },
            "validation_rules": {
                "name": "Minimum 5 characters, maximum 200 characters",
                "start_date": "Valid date format (YYYY-MM-DD)",
                "end_date": "Valid date format, must be after start_date",
                "scope": "Text field, no specific restrictions"
            }
        },
        
        "report": {
            "url": "/api/report/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a single field of a report",
            "permissions": "Report creator, engagement members, managers, or superusers",
            "editable_fields": ["note", "report_type"],
            "request_format": {
                "field": "string (field name)",
                "value": "mixed (new field value)"
            },
            "validation_rules": {
                "note": "Maximum 60 characters",
                "report_type": "Must be one of: Draft, Final, Verification"
            }
        },
        
        "leave": {
            "url": "/api/leave/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a single field of a leave request",
            "permissions": "Leave owner, managers, or superusers",
            "editable_fields": ["note", "start_date", "end_date", "leave_type"],
            "validation_rules": {
                "note": "Maximum 200 characters",
                "start_date": "Valid date format",
                "end_date": "Valid date format, must be after start_date",
                "leave_type": "Must be one of: Training, Vacation, Work from Home"
            }
        },
        
        "client": {
            "url": "/api/client/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a single field of a client",
            "permissions": "Managers or superusers only",
            "editable_fields": ["name", "acronym", "code"],
            "validation_rules": {
                "name": "Minimum 2 characters, maximum 200 characters",
                "acronym": "Alphanumeric characters only, maximum 10 characters",
                "code": "Numeric characters only, maximum 4 characters"
            }
        },
        
        "comment": {
            "url": "/api/comment/{id}/edit-field/",
            "method": "PATCH",
            "description": "Update a comment's body text",
            "permissions": "Comment author only",
            "editable_fields": ["body"],
            "validation_rules": {
                "body": "Minimum 3 characters"
            }
        },
        
        "batch_vulnerabilities": {
            "url": "/api/vulnerabilities/batch-edit/",
            "method": "PATCH",
            "description": "Batch update multiple vulnerabilities",
            "permissions": "Individual permissions checked per vulnerability",
            "request_format": {
                "updates": [
                    {
                        "id": "integer (vulnerability ID)",
                        "field": "string (field name)",
                        "value": "mixed (new field value)"
                    }
                ]
            },
            "example_request": {
                "updates": [
                    {"id": 1, "field": "status", "value": "Fixed"},
                    {"id": 2, "field": "severity", "value": "High"},
                    {"id": 3, "field": "status", "value": "Fixed"}
                ]
            }
        }
    },
    
    "error_responses": {
        "400": {
            "description": "Bad Request - Validation failed",
            "example": {
                "success": False,
                "message": "Validation failed",
                "errors": {
                    "title": ["Title must be at least 3 characters long"]
                },
                "timestamp": "2023-12-01T10:30:00Z"
            }
        },
        "403": {
            "description": "Forbidden - Permission denied",
            "example": {
                "success": False,
                "message": "You don't have permission to edit this vulnerability",
                "timestamp": "2023-12-01T10:30:00Z"
            }
        },
        "404": {
            "description": "Not Found - Object does not exist",
            "example": {
                "success": False,
                "message": "Object not found",
                "timestamp": "2023-12-01T10:30:00Z"
            }
        },
        "500": {
            "description": "Internal Server Error",
            "example": {
                "success": False,
                "message": "An error occurred while updating the field",
                "timestamp": "2023-12-01T10:30:00Z"
            }
        }
    },
    
    "frontend_integration": {
        "javascript_usage": {
            "description": "Use the provided InlineEditor JavaScript class",
            "initialization": """
// Initialize inline editor
const editor = new InlineEditor({
    baseUrl: '/api',
    showNotifications: true,
    validateOnBlur: true
});

// Enable inline editing on specific elements
editor.enableInlineEditing('[data-inline-edit]');
            """,
            "html_markup": """
<!-- Basic inline editable field -->
<span data-inline-edit="true" 
      data-model="vulnerability" 
      data-id="123" 
      data-field="title" 
      data-value="Current Title">
    Current Title
</span>

<!-- Table cell example -->
<td data-inline-edit="true" 
    data-model="engagement" 
    data-id="456" 
    data-field="name" 
    data-value="Engagement Name">
    Engagement Name
</td>
            """
        },
        
        "css_classes": {
            "description": "Include the inline-edit.css stylesheet",
            "key_classes": [
                "[data-inline-edit='true']",
                ".inline-edit-form",
                ".inline-edit-notifications",
                ".inline-edit-field-{fieldname}"
            ]
        },
        
        "events": {
            "inlineEditSuccess": {
                "description": "Fired when field is successfully updated",
                "detail": {
                    "field": "Field name that was updated",
                    "oldValue": "Previous field value",
                    "newValue": "New field value"
                }
            },
            "inlineEditError": {
                "description": "Fired when update fails",
                "detail": {
                    "field": "Field name that failed to update",
                    "error": "Error message"
                }
            }
        }
    },
    
    "security_considerations": {
        "csrf_protection": "All endpoints require valid CSRF token",
        "authentication": "User must be logged in",
        "permission_checks": "Per-object and per-field permission validation",
        "input_validation": "Server-side validation on all inputs",
        "sql_injection": "Prevented by Django ORM usage",
        "xss_protection": "HTML escaping in frontend display"
    },
    
    "performance_optimizations": {
        "database": [
            "Atomic transactions for consistency",
            "Optimized queries with select_related/prefetch_related",
            "Database indexes on frequently queried fields"
        ],
        "caching": [
            "Response caching for static field options",
            "Permission result caching per request"
        ],
        "frontend": [
            "Debounced validation",
            "Batch operations for multiple updates",
            "Progressive enhancement approach"
        ]
    },
    
    "testing": {
        "unit_tests": "Test individual endpoint functionality",
        "integration_tests": "Test complete edit workflows",
        "permission_tests": "Verify access control",
        "validation_tests": "Test input validation rules",
        "performance_tests": "Load testing for batch operations"
    }
}


USAGE_EXAMPLES = {
    "django_template": """
<!-- Load the CSS and JS files -->
<link rel="stylesheet" href="{% static 'css/inline-edit.css' %}">
<script src="{% static 'js/inline-edit.js' %}"></script>

<!-- In your table -->
<table class="table">
    <tbody>
        {% for vuln in vulnerabilities %}
        <tr>
            <td data-inline-edit="true" 
                data-model="vulnerability" 
                data-id="{{ vuln.id }}" 
                data-field="title" 
                data-value="{{ vuln.title }}">
                {{ vuln.title }}
            </td>
            <td data-inline-edit="true" 
                data-model="vulnerability" 
                data-id="{{ vuln.id }}" 
                data-field="severity" 
                data-value="{{ vuln.severity }}"
                class="inline-edit-field-severity {{ vuln.severity }}">
                {{ vuln.severity }}
            </td>
            <td data-inline-edit="true" 
                data-model="vulnerability" 
                data-id="{{ vuln.id }}" 
                data-field="status" 
                data-value="{{ vuln.status }}"
                class="inline-edit-field-status {{ vuln.status }}">
                {{ vuln.status }}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<script>
// Enable inline editing on page load
document.addEventListener('DOMContentLoaded', function() {
    inlineEditor.enableInlineEditing('[data-inline-edit]');
});
</script>
    """,
    
    "ajax_example": """
// Direct API call example
async function updateVulnerabilityTitle(vulnId, newTitle) {
    try {
        const response = await fetch(`/api/vulnerability/${vulnId}/edit-field/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                field: 'title',
                value: newTitle
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('Title updated successfully:', result.data);
            // Update UI
        } else {
            console.error('Update failed:', result.message);
            // Handle error
        }
    } catch (error) {
        console.error('Request failed:', error);
    }
}
    """,
    
    "batch_update_example": """
// Batch update multiple vulnerabilities
async function batchUpdateVulnerabilities(updates) {
    try {
        const response = await fetch('/api/vulnerabilities/batch-edit/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ updates })
        });
        
        const result = await response.json();
        
        console.log(`Updated ${result.data.updated_count} vulnerabilities`);
        if (result.data.errors.length > 0) {
            console.warn(`${result.data.error_count} errors occurred`);
        }
        
        return result;
    } catch (error) {
        console.error('Batch update failed:', error);
        throw error;
    }
}

// Usage
const updates = [
    { id: 1, field: 'status', value: 'Fixed' },
    { id: 2, field: 'severity', value: 'High' },
    { id: 3, field: 'status', value: 'Fixed' }
];

batchUpdateVulnerabilities(updates);
    """
}


def get_api_documentation():
    """Return the complete API documentation"""
    return API_DOCUMENTATION


def get_usage_examples():
    """Return usage examples"""
    return USAGE_EXAMPLES


def generate_markdown_docs():
    """Generate markdown documentation for the inline editing API"""
    docs = get_api_documentation()
    
    md_content = f"""# {docs['title']}

**Version:** {docs['version']}

{docs['description']}

## Authentication

{docs['authentication']['type']}

### Required Headers
"""
    
    for header, description in docs['authentication']['required_headers'].items():
        md_content += f"- `{header}`: {description}\n"
    
    md_content += "\n## API Endpoints\n"
    
    for endpoint_name, endpoint_info in docs['endpoints'].items():
        md_content += f"\n### {endpoint_name.title()}\n\n"
        md_content += f"**URL:** `{endpoint_info['url']}`\n"
        md_content += f"**Method:** `{endpoint_info['method']}`\n"
        md_content += f"**Description:** {endpoint_info['description']}\n"
        md_content += f"**Permissions:** {endpoint_info['permissions']}\n"
        
        if 'editable_fields' in endpoint_info:
            md_content += f"**Editable Fields:** {', '.join(endpoint_info['editable_fields'])}\n"
        
        if 'validation_rules' in endpoint_info:
            md_content += "\n**Validation Rules:**\n"
            for field, rule in endpoint_info['validation_rules'].items():
                md_content += f"- `{field}`: {rule}\n"
        
        md_content += "\n"
    
    return md_content