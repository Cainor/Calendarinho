from django.urls import path

from . import views



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
]
