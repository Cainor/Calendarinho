from django.urls import path

from . import views
from django.conf.urls import url


app_name = 'CalendarinhoApp'

urlpatterns = [
    path('', views.Dashboard, name='Dashboard'),
    path('Dashboard', views.Dashboard, name='Dashboard'),
    path('EmployeesTable', views.EmployeesTable, name='EmployeesTable'),
    path('EngagementsTable', views.EngagementsTable, name='EngagementsTable'),
    path('profile/<int:emp_id>/', views.profile, name='profile'),
    path('engagement/<int:eng_id>/', views.engagement, name='engagement'),
    path('EngagementsCalendar/', views.EngagementsCal, name='EngagementsCal'),
    path('EmployeesCalendar/overlap/', views.overlap, name='Overlap'),
    path('exportcsv/<int:empID>', views.exportCSV, name='exportCSV'),
    path('exportcsv/', views.exportCSV, name='exportCSV'),
    path('login', views.loginForm, name='login'),
    # path(regex=r'^login\/(?P<next>.*)$', views.loginForm, name='login_next'),
    url(regex=r'^login\/(?P<next>.*)$', view=views.loginForm),
    path('logout', views.logout_view, name='logout'),
]
