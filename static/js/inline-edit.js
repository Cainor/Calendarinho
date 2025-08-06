/**
 * Inline Editing JavaScript Utilities
 * Provides frontend support for seamless inline field editing
 */

class InlineEditor {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '/api';
        this.csrfToken = this.getCSRFToken();
        this.defaultOptions = {
            timeout: 30000,
            showNotifications: true,
            validateOnBlur: true,
            autoSave: false,
            autoSaveDelay: 1000,
            ...options
        };
        
        this.activeEditors = new Map();
        this.servicesCache = null;
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupNotificationContainer();
        this.loadServices(); // Load services on initialization
    }
    
    async loadServices() {
        try {
            const response = await fetch(`${this.baseUrl}/services/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success && data.data && data.data.services) {
                    this.servicesCache = data.data.services.map(service => ({
                        value: service.id,
                        label: service.display_name || service.name,
                        name: service.name
                    }));
                } else {
                    this.setFallbackServices();
                }
            } else {
                this.setFallbackServices();
            }
        } catch (error) {
            this.setFallbackServices();
        }
    }
    
    setFallbackServices() {
        this.servicesCache = [
            { value: 1, label: 'Penetration Testing', name: 'Penetration Testing' },
            { value: 2, label: 'Vulnerability Assessment', name: 'Vulnerability Assessment' },
            { value: 3, label: 'Code Review', name: 'Code Review' },
            { value: 4, label: 'Security Audit', name: 'Security Audit' },
            { value: 5, label: 'Red Team Assessment', name: 'Red Team Assessment' }
        ];
    }
    
    getCSRFToken() {
        // Get CSRF token from cookie or meta tag
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        if (cookieValue) return cookieValue;
        
        // Fallback to meta tag
        const metaTag = document.querySelector('meta[name=csrf-token]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    setupEventListeners() {
        // Listen for inline edit triggers
        document.addEventListener('click', (e) => {
            if (e.target.matches('.inline-editable')) {
                this.startEditing(e.target);
            }
        });
        
        // Handle escape key to cancel editing
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.cancelAllEditing();
            }
        });
        
        // Handle form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.matches('.inline-edit-form')) {
                e.preventDefault();
                this.handleFormSubmission(e.target);
            }
        });
    }
    
    setupNotificationContainer() {
        if (!document.getElementById('inline-edit-notifications')) {
            const container = document.createElement('div');
            container.id = 'inline-edit-notifications';
            container.className = 'inline-edit-notifications';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
    }
    
    async startEditing(element) {
        const modelType = element.dataset.model;
        const modelId = element.dataset.id;
        const fieldName = element.dataset.field;
        // Preserve spaces - use data-value first, then textContent WITHOUT trimming
        let currentValue = element.dataset.value || element.textContent;
        
        // If the element contains HTML (like <br> tags), extract text content but preserve spaces
        if (element.innerHTML !== element.textContent) {
            currentValue = element.textContent;
        }
        
        if (this.activeEditors.has(element)) {
            return; // Already editing
        }
        
        // For service_type, reload services before editing
        if (fieldName === 'service_type') {
            await this.loadServices();
        }
        
        // Create editing interface
        const editor = this.createEditor(element, {
            modelType,
            modelId,
            fieldName,
            currentValue
        });
        
        this.activeEditors.set(element, editor);
        
        // Replace element content with editor
        element.innerHTML = '';
        element.appendChild(editor);
        
        // Focus the input
        const input = editor.querySelector('input, textarea, select');
        if (input) {
            // Add event listeners to prevent interference with space key
            input.addEventListener('keydown', (e) => {
                // Don't let other handlers interfere with normal typing
                e.stopPropagation();
            });
            
            input.addEventListener('keypress', (e) => {
                // Don't let other handlers interfere with normal typing
                e.stopPropagation();
            });
            
            input.focus();
            if (input.type === 'text' || input.tagName === 'TEXTAREA') {
                input.select();
            }
        }
    }
    
    createEditor(element, config) {
        const { modelType, modelId, fieldName, currentValue } = config;
        
        const form = document.createElement('form');
        form.className = 'inline-edit-form';
        form.style.cssText = 'margin: 0; padding: 0; display: inline-block;';
        
        // Determine input type based on field name and model
        const inputType = this.getInputType(fieldName, modelType);
        let input;
        
        switch (inputType.type) {
            case 'textarea':
                input = document.createElement('textarea');
                input.value = currentValue;
                input.style.cssText = `
                    min-width: 500px; 
                    min-height: 60px; 
                    resize: vertical;
                    font-family: inherit;
                    font-size: inherit;
                `;
                break;
            case 'select':
                input = document.createElement('select');
                
                // Handle dynamic loading for certain fields
                if (inputType.loadDynamically && fieldName === 'service_type') {
                    this.loadServiceOptions(input, currentValue);
                } else {
                    inputType.options.forEach(option => {
                        const opt = document.createElement('option');
                        opt.value = option.value;
                        opt.textContent = option.label;
                        // For service_type, compare by name or id
                        if (fieldName === 'service_type') {
                            opt.selected = option.name === currentValue || option.value.toString() === currentValue.toString();
                        } else {
                            opt.selected = option.value === currentValue;
                        }
                        input.appendChild(opt);
                    });
                }
                break;
            case 'date':
                input = document.createElement('input');
                input.type = 'date';
                input.value = this.formatDateForInput(currentValue);
                break;
            default:
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
                input.style.cssText = 'min-width: 150px; font-family: inherit; font-size: inherit;';
        }
        
        input.name = fieldName;
        input.className = 'form-control form-control-sm';
        
        // Add buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'margin-top: 5px; white-space: nowrap;';
        
        const saveBtn = document.createElement('button');
        saveBtn.type = 'submit';
        saveBtn.className = 'btn btn-primary btn-sm me-1';
        saveBtn.textContent = 'Save';
        saveBtn.style.cssText = 'margin-right: 5px;';
        
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-secondary btn-sm';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.onclick = () => this.cancelEditing(element);
        
        buttonContainer.appendChild(saveBtn);
        buttonContainer.appendChild(cancelBtn);
        
        form.appendChild(input);
        form.appendChild(buttonContainer);
        
        // Store configuration
        form._config = config;
        form._element = element;
        
        return form;
    }
    
    getInputType(fieldName, modelType) {
        // Field-specific input types
        const fieldTypes = {
            description: { type: 'textarea' },
            scope: { type: 'textarea' },
            body: { type: 'textarea' },
            start_date: { type: 'date' },
            end_date: { type: 'date' },
            severity: { 
                type: 'select',
                options: [
                    { value: 'Critical', label: 'Critical' },
                    { value: 'High', label: 'High' },
                    { value: 'Medium', label: 'Medium' },
                    { value: 'Low', label: 'Low' }
                ]
            },
            status: {
                type: 'select',
                options: [
                    { value: 'Open', label: 'Open' },
                    { value: 'Fixed', label: 'Fixed' }
                ]
            },
            report_type: {
                type: 'select',
                options: [
                    { value: 'Draft', label: 'Draft' },
                    { value: 'Final', label: 'Final' },
                    { value: 'Verification', label: 'Verification' }
                ]
            },
            leave_type: {
                type: 'select',
                options: [
                    { value: 'Training', label: 'Training' },
                    { value: 'Vacation', label: 'Vacation' },
                    { value: 'Work from Home', label: 'Work from Home' }
                ]
            },
            service_type: {
                type: 'select',
                options: [], // Will be loaded dynamically
                loadDynamically: true
            }
        };
        
        // Special handling for service_type with dynamic options
        if (fieldName === 'service_type') {
            return {
                type: 'select',
                options: this.getServiceOptions()
            };
        }
        
        return fieldTypes[fieldName] || { type: 'text' };
    }
    
    getServiceOptions() {
        if (this.servicesCache && this.servicesCache.length > 0) {
            return this.servicesCache;
        }
        
        // Fallback options while services are loading
        return [
            { value: 1, label: 'Penetration Testing', name: 'Penetration Testing' },
            { value: 2, label: 'Vulnerability Assessment', name: 'Vulnerability Assessment' },
            { value: 3, label: 'Code Review', name: 'Code Review' },
            { value: 4, label: 'Security Audit', name: 'Security Audit' }
        ];
    }
    
    formatDateForInput(dateString) {
        if (!dateString) return '';
        
        // Try to parse the date
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return dateString; // Return as-is if not parseable
        }
        
        // Format as YYYY-MM-DD for HTML date input
        return date.toISOString().split('T')[0];
    }
    
    async handleFormSubmission(form) {
        const config = form._config;
        const element = form._element;
        const input = form.querySelector('input, textarea, select');
        const newValue = input.value;
        
        if (newValue === config.currentValue) {
            this.cancelEditing(element);
            return;
        }
        
        const saveBtn = form.querySelector('button[type="submit"]');
        const originalText = saveBtn.textContent;
        saveBtn.textContent = 'Saving...';
        saveBtn.disabled = true;
        
        try {
            const result = await this.saveField(config.modelType, config.modelId, config.fieldName, newValue);
            
            if (result.success) {
                // Update element with new value
                element.dataset.value = result.data.value;
                element.innerHTML = this.formatDisplayValue(result.data.formatted_value, config.fieldName);
                
                this.activeEditors.delete(element);
                
                if (this.defaultOptions.showNotifications) {
                    this.showNotification('Field updated successfully', 'success');
                }
                
                // Trigger custom event
                element.dispatchEvent(new CustomEvent('inlineEditSuccess', {
                    detail: { field: config.fieldName, oldValue: config.currentValue, newValue: result.data.value }
                }));
            } else {
                throw new Error(result.message || 'Save failed');
            }
        } catch (error) {
            // Log error for debugging
            if (window.console && window.console.error) {
                window.console.error('Inline edit error:', error);
            }
            saveBtn.textContent = originalText;
            saveBtn.disabled = false;
            
            if (this.defaultOptions.showNotifications) {
                this.showNotification(error.message || 'Failed to save changes', 'error');
            }
            
            // Trigger error event
            element.dispatchEvent(new CustomEvent('inlineEditError', {
                detail: { field: config.fieldName, error: error.message }
            }));
        }
    }
    
    async saveField(modelType, modelId, fieldName, value) {
        const url = `${this.baseUrl}/${modelType}/${modelId}/edit-field/`;
        
        const response = await fetch(url, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                field: fieldName,
                value: value
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    formatDisplayValue(value, fieldName) {
        if (!value && value !== 0) return '<em>Not set</em>';
        
        // Format based on field type
        if (fieldName.includes('date')) {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString();
            }
        }
        
        // Escape HTML for security
        return this.escapeHtml(value.toString());
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    cancelEditing(element) {
        const editor = this.activeEditors.get(element);
        if (editor) {
            const config = editor._config;
            element.innerHTML = this.formatDisplayValue(config.currentValue, config.fieldName);
            this.activeEditors.delete(element);
        }
    }
    
    cancelAllEditing() {
        for (const [element] of this.activeEditors) {
            this.cancelEditing(element);
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('inline-edit-notifications');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.cssText = 'margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    // Batch operations
    async batchUpdate(updates) {
        const url = `${this.baseUrl}/vulnerabilities/batch-edit/`;
        
        const response = await fetch(url, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ updates })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    // Utility methods for integrating with existing code
    enableInlineEditing(selector) {
        document.querySelectorAll(selector).forEach(element => {
            if (!element.dataset.inlineEdit) {
                element.dataset.inlineEdit = 'true';
                element.style.cursor = 'pointer';
                element.title = 'Click to edit';
                
                // Add visual indicator
                element.addEventListener('mouseenter', () => {
                    element.style.backgroundColor = '#f8f9fa';
                });
                
                element.addEventListener('mouseleave', () => {
                    if (!this.activeEditors.has(element)) {
                        element.style.backgroundColor = '';
                    }
                });
            }
        });
    }
    
    disableInlineEditing(selector) {
        document.querySelectorAll(selector).forEach(element => {
            delete element.dataset.inlineEdit;
            element.style.cursor = '';
            element.title = '';
            element.style.backgroundColor = '';
        });
    }
    
    async loadServiceOptions(selectElement, currentValue) {
        // Add loading option
        const loadingOption = document.createElement('option');
        loadingOption.value = '';
        loadingOption.textContent = 'Loading services...';
        selectElement.appendChild(loadingOption);
        selectElement.disabled = true;
        
        try {
            const response = await fetch(`${this.baseUrl}/services/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Clear loading option
            selectElement.innerHTML = '';
            selectElement.disabled = false;
            
            if (data.success && data.data.services) {
                data.data.services.forEach(service => {
                    const opt = document.createElement('option');
                    opt.value = service.id;
                    opt.textContent = service.display_name;
                    // Compare by ID first, then by name for backward compatibility
                    opt.selected = service.id.toString() === currentValue.toString() || service.name === currentValue;
                    selectElement.appendChild(opt);
                });
            } else {
                throw new Error(data.message || 'Failed to load services');
            }
        } catch (error) {
            if (window.console && window.console.error) {
                window.console.error('Error loading services:', error);
            }
            selectElement.innerHTML = '';
            selectElement.disabled = false;
            
            // Add error option
            const errorOption = document.createElement('option');
            errorOption.value = '';
            errorOption.textContent = 'Error loading services';
            selectElement.appendChild(errorOption);
            
            if (this.defaultOptions.showNotifications) {
                this.showNotification('Failed to load services', 'error');
            }
        }
    }
}

// Employee Management Utility Class for Inline Editing
class EmployeeManager {
    constructor(inlineEditor) {
        this.editor = inlineEditor;
        this.baseUrl = inlineEditor.baseUrl;
        this.csrfToken = inlineEditor.csrfToken;
    }
    
    async getEngagementEmployees(engagementId) {
        try {
            const response = await fetch(`${this.baseUrl}/engagement/${engagementId}/employees/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (window.console && window.console.error) {
                window.console.error('Error fetching engagement employees:', error);
            }
            throw error;
        }
    }
    
    async getAvailableEmployees() {
        try {
            const response = await fetch(`${this.baseUrl}/employees/available/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (window.console && window.console.error) {
                window.console.error('Error fetching available employees:', error);
            }
            throw error;
        }
    }
    
    async addEmployeeToEngagement(engagementId, employeeId, checkConflicts = true) {
        try {
            const response = await fetch(`${this.baseUrl}/engagement/${engagementId}/add-employee/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    check_conflicts: checkConflicts
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (window.console && window.console.error) {
                window.console.error('Error adding employee to engagement:', error);
            }
            throw error;
        }
    }
    
    async removeEmployeeFromEngagement(engagementId, employeeId) {
        try {
            const response = await fetch(`${this.baseUrl}/engagement/${engagementId}/remove-employee/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    employee_id: employeeId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (window.console && window.console.error) {
                window.console.error('Error removing employee from engagement:', error);
            }
            throw error;
        }
    }
    
    // UI Helper methods for employee management
    createEmployeeManagementInterface(engagementId, containerElement) {
        const container = document.createElement('div');
        container.className = 'employee-management-interface';
        container.innerHTML = `
            <div class="current-employees mb-3">
                <h6>Current Team Members</h6>
                <div class="employees-list" data-engagement-id="${engagementId}">
                    <div class="loading">Loading team members...</div>
                </div>
            </div>
            <div class="add-employee">
                <h6>Add Team Member</h6>
                <select class="form-control form-control-sm mb-2" id="available-employees-${engagementId}">
                    <option value="">Loading employees...</option>
                </select>
                <button class="btn btn-primary btn-sm" onclick="employeeManager.addSelectedEmployee(${engagementId})">
                    Add Employee
                </button>
            </div>
        `;
        
        if (containerElement) {
            containerElement.appendChild(container);
        }
        
        // Load current employees and available employees
        this.loadCurrentEmployees(engagementId);
        this.loadAvailableEmployeesDropdown(engagementId);
        
        return container;
    }
    
    async loadCurrentEmployees(engagementId) {
        const listContainer = document.querySelector(`[data-engagement-id="${engagementId}"]`);
        if (!listContainer) return;
        
        try {
            const result = await this.getEngagementEmployees(engagementId);
            
            if (result.success) {
                const employees = result.data.employees;
                
                if (employees.length === 0) {
                    listContainer.innerHTML = '<em class="text-muted">No team members assigned</em>';
                    return;
                }
                
                listContainer.innerHTML = employees.map(emp => `
                    <div class="employee-item d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
                        <div>
                            <strong>${emp.full_name}</strong> 
                            <small class="text-muted">(${emp.user_type})</small>
                        </div>
                        <button class="btn btn-danger btn-sm" 
                                onclick="employeeManager.removeEmployee(${engagementId}, ${emp.id}, '${emp.full_name}')"
                                title="Remove from engagement">
                            ×
                        </button>
                    </div>
                `).join('');
            } else {
                listContainer.innerHTML = '<em class="text-danger">Error loading team members</em>';
            }
        } catch (error) {
            listContainer.innerHTML = '<em class="text-danger">Error loading team members</em>';
            if (window.console && window.console.error) {
                window.console.error('Error loading current employees:', error);
            }
        }
    }
    
    async loadAvailableEmployeesDropdown(engagementId) {
        const select = document.getElementById(`available-employees-${engagementId}`);
        if (!select) return;
        
        try {
            const result = await this.getAvailableEmployees();
            
            if (result.success) {
                const employees = result.data.employees;
                
                select.innerHTML = '<option value="">Select an employee...</option>';
                employees.forEach(emp => {
                    const option = document.createElement('option');
                    option.value = emp.id;
                    option.textContent = `${emp.full_name} (${emp.status_label})`;
                    option.className = emp.status === 'Available' ? 'text-success' : 'text-warning';
                    select.appendChild(option);
                });
            } else {
                select.innerHTML = '<option value="">Error loading employees</option>';
            }
        } catch (error) {
            select.innerHTML = '<option value="">Error loading employees</option>';
            if (window.console && window.console.error) {
                window.console.error('Error loading available employees:', error);
            }
        }
    }
    
    async addSelectedEmployee(engagementId) {
        const select = document.getElementById(`available-employees-${engagementId}`);
        const employeeId = select.value;
        
        if (!employeeId) {
            this.editor.showNotification('Please select an employee', 'warning');
            return;
        }
        
        try {
            const result = await this.addEmployeeToEngagement(engagementId, employeeId);
            
            if (result.success) {
                this.editor.showNotification('Employee added successfully', 'success');
                // Refresh the lists
                this.loadCurrentEmployees(engagementId);
                this.loadAvailableEmployeesDropdown(engagementId);
                select.value = '';
            } else {
                this.editor.showNotification(result.message || 'Failed to add employee', 'error');
            }
        } catch (error) {
            this.editor.showNotification('Error adding employee', 'error');
            if (window.console && window.console.error) {
                window.console.error('Error adding employee:', error);
            }
        }
    }
    
    async removeEmployee(engagementId, employeeId, employeeName) {
        if (!confirm(`Are you sure you want to remove ${employeeName} from this engagement?`)) {
            return;
        }
        
        try {
            const result = await this.removeEmployeeFromEngagement(engagementId, employeeId);
            
            if (result.success) {
                this.editor.showNotification('Employee removed successfully', 'success');
                // Refresh the lists
                this.loadCurrentEmployees(engagementId);
                this.loadAvailableEmployeesDropdown(engagementId);
            } else {
                this.editor.showNotification(result.message || 'Failed to remove employee', 'error');
            }
        } catch (error) {
            this.editor.showNotification('Error removing employee', 'error');
            if (window.console && window.console.error) {
                window.console.error('Error removing employee:', error);
            }
        }
    }
}

// Initialize global inline editor instance
window.inlineEditor = new InlineEditor({
    showNotifications: true,
    validateOnBlur: true
});

// Initialize employee manager
window.employeeManager = new EmployeeManager(window.inlineEditor);

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { InlineEditor, EmployeeManager };
}