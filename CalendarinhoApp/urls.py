from django.urls import path

from . import views
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
    path('EmployeesTable', views.EmployeesTable, name='EmployeesTable'),
    path('EngagementsTable', views.EngagementsTable, name='EngagementsTable'),
    path('counterTable',views.counterEmpSvc, name='counterEmpSvc'),
    path('EpmTable',views.EpmTable, name='EpmTable'),
    path('profile/<int:emp_id>/', views.profile, name='profile'),
    path('engagement/<int:eng_id>/', views.engagement, name='engagement'),
    path('projectManager/<int:projmgr_id>/', views.projectManager, name='projectManager'),
    path('EngagementsCalendar/', views.EngagementsCal, name='EngagementsCal'),
    path('EmployeesCalendar/', views.EmployeesCal, name='EmployeesCal'),
    path('EmployeesCalendar/overlap/', views.overlap, name='Overlap'),
    path('LeavesCalendar/', views.LeavesCal, name='LeavesCal'),
    path('exportcsv/<int:empID>', views.exportCSV, name='exportCSV'),
    path('exportcsv/<slug:slug>', views.exportCSV, name='exportCSV'),
    path('exportcsv/', views.exportCSV, name='exportCSV'),
    path('engagement/<int:eng_id>/Reports/', views.uploadReport, name='uploadReport'),
    path('download/<uuid:refUUID>', views.downloadReport, name='downloadReport'),
    path('delete/<uuid:refUUID>', views.deleteReport, name='deleteReport'),
    
    
    path('login', views.loginForm, name='login'),
    re_path(r'^login\/(?P<next>.*)$', view=views.loginForm, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('client/<int:cli_id>/', views.client, name='client'),
    path('ClientsTable', views.ClientsTable, name='ClientsTable'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='CalendarinhoApp/password_reset_confirm.html', success_url=reverse_lazy(
            'CalendarinhoApp:password_reset_complete'), form_class=MySetPasswordForm), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='CalendarinhoApp/password_reset_complete.html'), name='password_reset_complete'),
    path('DeleteComment/<int:commentID>',
         views.deleteMyComment, name='deleteMyComment'),

    path('forgetpassword',views.forgetPasswordInit, name='forgetpasswordInit'),
    path('forgetpasswordOTP',views.forgetpasswordOTP, name='forgetpasswordOTP'),
    path('forgetpasswordEnd',views.forgetpasswordEnd, name='forgetpasswordEnd'),
    

    path("ToggleTheme",views.toggleTheme, name="ToggleTheme")
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)