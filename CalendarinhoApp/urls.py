from django.urls import path

from . import views
from . import authentication
from . import engagement
from . import employee
from . import client
from . import service
from . import api_filters
from . import vulnerabilities
from . import api_performance
from . import api_mobile
from . import api_docs
from . import api_inline_edit
from django.urls import re_path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from users.forms import MySetPasswordForm
from django.conf import settings
from django.conf.urls.static import static

app_name = 'CalendarinhoApp'

urlpatterns = [
    path('', views.Dashboard, name='Dashboard'),
    path('Dashboard', views.Dashboard, name='Dashboard'),
    path('managerDashboard', views.managerDashboard, name='managerDashboard'),
    path('EmployeesTable', employee.EmployeesTable, name='EmployeesTable'),
    path('EngagementsTable', engagement.EngagementsTable, name='EngagementsTable'),
    path('counterTable',views.counterEmpSvc, name='counterEmpSvc'),
    path('profile/<int:emp_id>/', employee.profile, name='profile'),
    path('engagement/<int:eng_id>/', engagement.engagement, name='engagement'),
    path('projectManager/<int:projmgr_id>/', employee.projectManager, name='projectManager'),
    path('Engagement/add', engagement.EngagementCreate, name='EngagementCreate'),
    path('EngagementsCalendar/', engagement.EngagementsCal, name='EngagementsCal'),
    path('EmployeesCalendar/', employee.EmployeesCal, name='EmployeesCal'),
    path('EmployeesCalendar/overlap/', employee.overlap, name='Overlap'),
    path('Leave/add', employee.LeaveCreate, name='LeaveCreate'),
    path('LeavesCalendar/', employee.LeavesCal, name='LeavesCal'),
    path('exportcsv/<int:empID>', views.exportCSV, name='exportCSV'),
    path('exportcsv/<slug:slug>', views.exportCSV, name='exportCSV'),
    path('exportcsv/', views.exportCSV, name='exportCSV'),
    path('engagement/<int:eng_id>/Reports/', engagement.uploadReport, name='uploadReport'),
    path('download/<uuid:refUUID>', engagement.downloadReport, name='downloadReport'),
    path('delete/<uuid:refUUID>', engagement.deleteReport, name='deleteReport'),
    
    # AJAX vulnerability management endpoints
    path('vulnerability/<int:vuln_id>/toggle-status/', engagement.toggleVulnerabilityStatus, name='toggleVulnerabilityStatus'),
    path('vulnerability/<int:vuln_id>/update-title/', engagement.updateVulnerabilityTitle, name='updateVulnerabilityTitle'),
    path('vulnerability/<int:vuln_id>/delete/', engagement.deleteVulnerability, name='deleteVulnerability'),
    path('engagement/<int:eng_id>/add-vulnerabilities/', engagement.addVulnerabilities, name='addVulnerabilities'),
    
    # API endpoints for enhanced data
    path('api/employee-stats/', service.api_employee_stats, name='api_employee_stats'),
    path('api/client-stats/', service.api_client_stats, name='api_client_stats'),
    path('api/engagement-stats/', service.api_engagement_stats, name='api_engagement_stats'),
    path('api/workload-distribution/', service.api_workload_distribution, name='api_workload_distribution'),
    path('api/availability-matrix/', service.api_availability_matrix, name='api_availability_matrix'),
    path('api/client-risk-assessment/', service.api_client_risk_assessment, name='api_client_risk_assessment'),
    path('api/timeline-conflicts/', service.api_timeline_conflicts, name='api_timeline_conflicts'),
    path('api/dashboard-summary/', service.api_dashboard_summary, name='api_dashboard_summary'),
    
    # Phase 2 Advanced Filtering and Bulk Operations API endpoints
    path('api/employees/filtered/', api_filters.api_employees_filtered, name='api_employees_filtered'),
    path('api/clients/filtered/', api_filters.api_clients_filtered, name='api_clients_filtered'),
    path('api/engagements/filtered/', api_filters.api_engagements_filtered, name='api_engagements_filtered'),
    path('api/vulnerabilities/filtered/', api_filters.api_vulnerabilities_filtered, name='api_vulnerabilities_filtered'),
    path('api/vulnerabilities/bulk-update/', api_filters.api_bulk_vulnerability_update, name='api_bulk_vulnerability_update'),
    path('api/vulnerabilities/bulk-delete/', api_filters.api_bulk_vulnerability_delete, name='api_bulk_vulnerability_delete'),
    path('api/mobile-data/', api_filters.api_mobile_optimized_data, name='api_mobile_optimized_data'),
    path('api/filter-options/', api_filters.api_filter_options, name='api_filter_options'),
    path('api/vulnerability-analytics/', service.api_vulnerability_analytics, name='api_vulnerability_analytics'),
    path('api/performance-metrics/', service.api_performance_metrics, name='api_performance_metrics'),
    path('api/search-suggestions/', service.api_search_suggestions, name='api_search_suggestions'),
    
    # Vulnerability management endpoints
    path('vulnerabilities/', vulnerabilities.vulnerabilities_table, name='vulnerabilities_table'),
    path('vulnerability/<int:vuln_id>/', vulnerabilities.vulnerability_detail, name='vulnerability_detail'),
    path('vulnerabilities/analytics/', vulnerabilities.vulnerability_analytics, name='vulnerability_analytics'),
    path('vulnerabilities/statistics/', vulnerabilities.vulnerability_statistics, name='vulnerability_statistics'),
    path('engagement/<int:eng_id>/vulnerabilities/', vulnerabilities.engagement_vulnerabilities, name='engagement_vulnerabilities'),
    path('client/<int:cli_id>/vulnerabilities/', vulnerabilities.client_vulnerabilities, name='client_vulnerabilities'),
    path('vulnerabilities/export/', vulnerabilities.export_vulnerabilities, name='export_vulnerabilities'),
    
    # Performance optimization endpoints
    path('api/lazy/employees/', api_performance.api_lazy_load_employees, name='api_lazy_load_employees'),
    path('api/lazy/engagements/', api_performance.api_lazy_load_engagements, name='api_lazy_load_engagements'),
    path('api/lazy/clients/', api_performance.api_lazy_load_clients, name='api_lazy_load_clients'),
    path('api/dashboard-widgets/', api_performance.api_dashboard_widgets, name='api_dashboard_widgets'),
    path('api/prefetch/', api_performance.api_prefetch_data, name='api_prefetch_data'),
    path('api/search-cache-warm/', api_performance.api_search_cache_warm, name='api_search_cache_warm'),
    
    # Mobile-optimized API endpoints
    path('api/mobile/dashboard/', api_mobile.api_mobile_dashboard, name='api_mobile_dashboard'),
    path('api/mobile/engagements/', api_mobile.api_mobile_engagements, name='api_mobile_engagements'),
    path('api/mobile/clients/', api_mobile.api_mobile_clients, name='api_mobile_clients'),
    path('api/mobile/vulnerabilities/', api_mobile.api_mobile_vulnerabilities, name='api_mobile_vulnerabilities'),
    path('api/mobile/employees/', api_mobile.api_mobile_employees, name='api_mobile_employees'),
    path('api/mobile/quick-actions/', api_mobile.api_mobile_quick_actions, name='api_mobile_quick_actions'),
    
    # API Documentation
    path('api/docs/', api_docs.api_documentation, name='api_documentation'),
    
    # Inline Editing API Endpoints
    path('api/vulnerability/<int:vuln_id>/edit-field/', api_inline_edit.update_vulnerability_field, name='api_update_vulnerability_field'),
    path('api/engagement/<int:eng_id>/edit-field/', api_inline_edit.update_engagement_field, name='api_update_engagement_field'),
    path('api/engagement/<int:eng_id>/edit-field-enhanced/', api_inline_edit.update_engagement_field_enhanced, name='api_update_engagement_field_enhanced'),
    path('api/report/<int:report_id>/edit-field/', api_inline_edit.update_report_field, name='api_update_report_field'),
    path('api/leave/<int:leave_id>/edit-field/', api_inline_edit.update_leave_field, name='api_update_leave_field'),
    path('api/client/<int:client_id>/edit-field/', api_inline_edit.update_client_field, name='api_update_client_field'),
    path('api/comment/<int:comment_id>/edit-field/', api_inline_edit.update_comment_field, name='api_update_comment_field'),
    path('api/vulnerabilities/batch-edit/', api_inline_edit.batch_update_vulnerabilities, name='api_batch_update_vulnerabilities'),
    
    # Services API
    path('api/services/', api_inline_edit.get_services, name='api_get_services'),
    
    # Employee Management API for Inline Editing
    path('api/employees/available/', api_inline_edit.get_available_employees, name='api_get_available_employees'),
    path('api/engagement/<int:eng_id>/employees/', api_inline_edit.get_engagement_employees, name='api_get_engagement_employees'),
    path('api/engagement/<int:eng_id>/add-employee/', api_inline_edit.add_employee_to_engagement, name='api_add_employee_to_engagement'),
    path('api/engagement/<int:eng_id>/remove-employee/', api_inline_edit.remove_employee_from_engagement, name='api_remove_employee_from_engagement'),
    
    # API Documentation and Testing
    path('api/inline-edit/docs/', api_inline_edit.inline_edit_api_docs, name='api_inline_edit_docs'),
    path('api/inline-edit/test/', api_inline_edit.inline_edit_test, name='api_inline_edit_test'),
    path('debug-inline/', views.debug_inline, name='debug_inline'),
    
    path('login', authentication.loginForm, name='login'),
    re_path(r'^login\/(?P<next>.*)$', view=authentication.loginForm, name='login'),
    path('logout', authentication.logout_view, name='logout'),

    path('client/add', client.ClientCreate, name='ClientCreate'),
    path('client/<int:cli_id>/', client.client, name='client'),
    path('ClientsTable', client.ClientsTable, name='ClientsTable'),
    
    path('service/add', service.ServiceCreate, name='ServiceCreate'),
    
    path('DeleteComment/<int:commentID>',
         engagement.deleteMyComment, name='deleteMyComment'),
    
    # Mention system API endpoints
    path('api/engagement/<int:eng_id>/search-users/', 
         engagement.api_search_users_for_mention, name='api_search_users_for_mention'),

    path('forgetpassword',authentication.forgetPasswordInit, name='forgetpasswordInit'),
    path('forgetpasswordOTP',authentication.forgetpasswordOTP, name='forgetpasswordOTP'),
    path('forgetpasswordEnd',authentication.forgetpasswordEnd, name='forgetpasswordEnd'),

    path("ToggleTheme",views.toggleTheme, name="ToggleTheme")
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)