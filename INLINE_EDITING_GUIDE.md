# Calendarinho Inline Editing System

A comprehensive, accessible, and mobile-responsive inline editing solution for rapid UI updates without page navigation.

## 🚀 Quick Start

### Basic Implementation

1. **Add the CSS and JavaScript** (already included in BaseNew.html):
```html
<link href="{% static 'css/inline-edit.css' %}" rel="stylesheet">
<script src="{% static 'js/inline-edit.js' %}"></script>
```

2. **Make any element editable**:
```html
<span class="inline-editable" 
      data-model="engagement" 
      data-field="name" 
      data-id="123"
      data-type="text">Current Value</span>
```

3. **Or use the template helper**:
```html
{% include 'CalendarinhoApp/includes/inline_edit_field.html' with model='engagement' field='name' object_id=engagement.id value=engagement.name type='text' %}
```

## 📋 Data Attributes Reference

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `data-model` | ✅ | Model name for API endpoint | `engagement`, `vulnerability`, `client` |
| `data-field` | ✅ | Field name to update | `name`, `title`, `description` |
| `data-id` | ✅ | Object ID | `123` |
| `data-type` | ❌ | Input type | `text`, `textarea`, `select`, `date`, `number` |
| `data-required` | ❌ | Mark field as required | `true` |
| `data-placeholder` | ❌ | Placeholder text | `Enter name...` |
| `data-min-length` | ❌ | Minimum length validation | `3` |
| `data-max-length` | ❌ | Maximum length validation | `200` |
| `data-options` | ❌ | JSON options for select | `[{"value":"High","label":"High"}]` |

## 🎯 Field Types

### Text Input
```html
<span class="inline-editable" 
      data-model="client" 
      data-field="name" 
      data-id="1"
      data-type="text"
      data-required="true"
      data-max-length="200">Client Name</span>
```

### Textarea
```html
<span class="inline-editable inline-edit-multiline" 
      data-model="engagement" 
      data-field="scope" 
      data-id="1"
      data-type="textarea"
      data-placeholder="Enter scope details...">Project scope</span>
```

### Select Dropdown
```html
<span class="inline-editable badge badge-warning" 
      data-model="vulnerability" 
      data-field="severity" 
      data-id="1"
      data-type="select"
      data-options='[{"value":"Critical","label":"Critical"},{"value":"High","label":"High"},{"value":"Medium","label":"Medium"},{"value":"Low","label":"Low"}]'>High</span>
```

### Date Field
```html
<span class="inline-editable font-monospace" 
      data-model="engagement" 
      data-field="start_date" 
      data-id="1"
      data-type="date"
      data-required="true">2024-01-15</span>
```

### Number Field
```html
<span class="inline-editable" 
      data-model="engagement" 
      data-field="budget" 
      data-id="1"
      data-type="number">25000</span>
```

## 🎨 Styling Options

### CSS Classes

| Class | Purpose |
|-------|---------|
| `inline-editable` | Base class (required) |
| `inline-edit-compact` | Smaller padding and font size |
| `inline-edit-multiline` | Better line spacing for multiline text |
| `inline-edit-required` | Adds red asterisk |
| `inline-edit-disabled` | Disables editing |

### Context Integration

```html
<!-- In vulnerability items -->
<div class="vulnerability-item">
    <span class="inline-editable vulnerability-title" 
          data-model="vulnerability" 
          data-field="title" 
          data-id="1">SQL Injection</span>
</div>

<!-- In tables -->
<td>
    <span class="inline-editable" 
          data-model="report" 
          data-field="note" 
          data-id="1">Report note</span>
</td>

<!-- In cards -->
<div class="card">
    <div class="card-body">
        <h5 class="inline-editable" 
            data-model="engagement" 
            data-field="name" 
            data-id="1">Project Name</h5>
    </div>
</div>
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Click` or `Enter` | Start editing |
| `Enter` | Save changes (text fields) |
| `Escape` | Cancel editing |
| `Tab` | Navigate between fields |
| `Click outside` | Save changes |
| `Alt + E` | Highlight all editable fields |

## 🔧 JavaScript API

### Basic Configuration
```javascript
// Access the global instance
window.inlineEditManager.updateConfig({
    autoSave: true,
    saveDelay: 1500,
    
    onSaveSuccess: function(element, newValue, result) {
        console.log('Saved:', element.dataset.field, newValue);
    },
    
    onSaveError: function(element, error) {
        console.error('Error:', error);
    }
});
```

### Custom Callbacks
```javascript
document.addEventListener('DOMContentLoaded', function() {
    if (window.inlineEditManager) {
        window.inlineEditManager.updateConfig({
            onSaveSuccess: function(element, newValue, result) {
                // Update related UI elements
                if (element.dataset.field === 'status') {
                    updateStatusIndicators(element.closest('.vulnerability-item'));
                }
                
                // Refresh statistics
                if (element.dataset.model === 'vulnerability') {
                    updateVulnerabilityStats();
                }
            }
        });
    }
});
```

### Dynamic Field Addition
```javascript
// Add inline editing to dynamically created elements
const newElement = document.createElement('span');
newElement.textContent = 'New Value';

window.inlineEditManager.addEditableElement(newElement, {
    model: 'engagement',
    field: 'name',
    id: '123',
    type: 'text'
});
```

## 🛡️ Backend API Requirements

The inline editing system expects API endpoints at:
```
POST /api/{model}/{id}/edit-field/
```

### Request Format
```javascript
{
    "field": "field_name",
    "value": "new_value"
}
```

### Response Format
```javascript
// Success
{
    "success": true,
    "message": "Field updated successfully"
}

// Error
{
    "success": false,
    "error": "Validation error message"
}
```

### Example Django View
```python
@require_http_methods(["POST"])
@csrf_protect
def edit_field(request, model, id):
    try:
        data = json.loads(request.body)
        field_name = data.get('field')
        new_value = data.get('value')
        
        # Get model and object
        model_class = get_model_class(model)  # Your implementation
        obj = get_object_or_404(model_class, id=id)
        
        # Permission check
        if not obj.can_be_edited_by(request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Field validation
        if field_name not in obj.get_editable_fields(request.user):
            return JsonResponse({'success': False, 'error': 'Field not editable'})
        
        # Update field
        setattr(obj, field_name, new_value)
        obj.full_clean()  # Validate
        obj.save()
        
        return JsonResponse({'success': True})
        
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Update failed'})
```

## 📱 Mobile Optimization

### Touch Targets
- Minimum 44px height on mobile devices
- Larger padding and font sizes
- Touch-friendly controls

### Mobile-Specific Features
- Controls appear at bottom of screen
- Optimized for thumb navigation
- Prevents iOS zoom with font-size: 16px

### Responsive Behavior
```css
@media (max-width: 768px) {
    .inline-edit-controls {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
    }
    
    .inline-edit-btn {
        min-height: 44px;
        min-width: 80px;
    }
}
```

## ♿ Accessibility Features

### Screen Reader Support
- ARIA labels and roles
- Keyboard navigation
- Screen reader announcements for state changes

### High Contrast Mode
```css
@media (prefers-contrast: high) {
    .inline-editable {
        border: 2px solid currentColor;
    }
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
    .inline-editable {
        transition: none;
        animation: none;
    }
}
```

## 🎯 Best Practices

### 1. Field Selection
- Prioritize frequently edited fields
- Avoid editing critical system fields inline
- Consider field relationships and dependencies

### 2. User Experience
- Provide clear visual feedback
- Use appropriate input types
- Include helpful placeholder text
- Validate on both client and server

### 3. Performance
- Use debounced auto-save
- Batch related updates when possible
- Show loading states for slow operations

### 4. Security
- Always validate on the server
- Check permissions before editing
- Use CSRF protection
- Sanitize input values

## 🔧 Customization Examples

### Custom Styling
```css
/* Custom theme for vulnerability fields */
.vulnerability-item .inline-editable[data-field="title"] {
    background: rgba(231, 74, 59, 0.1);
    border-left: 4px solid #e74a3b;
    font-weight: 600;
}

/* Success state customization */
.inline-success.vulnerability-title {
    animation: bounceIn 0.6s ease-out;
}
```

### Integration with Existing Components
```html
<!-- Bootstrap badge with inline editing -->
<span class="badge badge-warning inline-editable" 
      data-model="vulnerability" 
      data-field="severity" 
      data-id="1"
      data-type="select"
      data-options='[{"value":"High","label":"High"},{"value":"Medium","label":"Medium"}]'>High</span>

<!-- Card title with inline editing -->
<div class="card">
    <div class="card-header">
        <h5 class="inline-editable mb-0" 
            data-model="engagement" 
            data-field="name" 
            data-id="1"
            data-type="text">Engagement Name</h5>
    </div>
</div>
```

## 🐛 Troubleshooting

### Common Issues

1. **Fields not editable**
   - Check CSS and JS are loaded
   - Verify data attributes are correct
   - Check browser console for errors

2. **Save not working**
   - Verify API endpoint exists
   - Check CSRF token
   - Review server logs for errors

3. **Styling issues**
   - Check CSS specificity conflicts
   - Verify responsive breakpoints
   - Test on different devices

### Debug Mode
```javascript
// Enable debug logging
window.inlineEditManager.updateConfig({
    debug: true,
    onSaveStart: function(element, value) {
        console.log('Saving:', element.dataset, value);
    }
});
```

## 🚀 Advanced Features

### Conditional Editing
```html
<!-- Only editable by managers -->
{% if user.is_superuser or user.user_type == 'M' %}
    <span class="inline-editable" data-model="engagement" data-field="budget" data-id="1">$25,000</span>
{% else %}
    <span>$25,000</span>
{% endif %}
```

### Dependent Fields
```javascript
window.inlineEditManager.updateConfig({
    onSaveSuccess: function(element, newValue, result) {
        // Update dependent fields
        if (element.dataset.field === 'start_date') {
            updateEndDateConstraints(newValue);
        }
    }
});
```

### Batch Operations
```javascript
// Save multiple fields at once
function saveAllChanges() {
    const editableFields = document.querySelectorAll('.inline-editing');
    editableFields.forEach(field => {
        window.inlineEditManager.saveEdit(field);
    });
}
```

This inline editing system provides a seamless, accessible, and powerful way to edit content directly within your Calendarinho application, eliminating the need for separate edit pages and improving the overall user experience.