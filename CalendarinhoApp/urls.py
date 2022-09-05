from django.urls import path

from . import views
from . import authentication
from . import engagement
from . import employee
from . import client
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
    path('EngagementsCalendar/', engagement.EngagementsCal, name='EngagementsCal'),
    path('EmployeesCalendar/', employee.EmployeesCal, name='EmployeesCal'),
    path('EmployeesCalendar/overlap/', employee.overlap, name='Overlap'),
    path('LeavesCalendar/', employee.LeavesCal, name='LeavesCal'),
    path('exportcsv/<int:empID>', views.exportCSV, name='exportCSV'),
    path('exportcsv/<slug:slug>', views.exportCSV, name='exportCSV'),
    path('exportcsv/', views.exportCSV, name='exportCSV'),
    path('engagement/<int:eng_id>/Reports/', engagement.uploadReport, name='uploadReport'),
    path('download/<uuid:refUUID>', engagement.downloadReport, name='downloadReport'),
    path('delete/<uuid:refUUID>', engagement.deleteReport, name='deleteReport'),
    
    
    path('login', authentication.loginForm, name='login'),
    re_path(r'^login\/(?P<next>.*)$', view=authentication.loginForm, name='login'),
    path('logout', authentication.logout_view, name='logout'),
    path('client/<int:cli_id>/', client.client, name='client'),
    path('ClientsTable', client.ClientsTable, name='ClientsTable'),
    
    path('DeleteComment/<int:commentID>',
         engagement.deleteMyComment, name='deleteMyComment'),

    path('forgetpassword',authentication.forgetPasswordInit, name='forgetpasswordInit'),
    path('forgetpasswordOTP',authentication.forgetpasswordOTP, name='forgetpasswordOTP'),
    path('forgetpasswordEnd',authentication.forgetpasswordEnd, name='forgetpasswordEnd'),

    path("ToggleTheme",views.toggleTheme, name="ToggleTheme")
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)