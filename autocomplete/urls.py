from django.urls import re_path

from . import views
from django.conf.urls import url

from autocomplete.views import EmployeeNameAutocomplete, ClientNameAutocomplete, ServiceNameAutocomplete


app_name = 'autocomplete'
urlpatterns = [
    re_path(r'^employee-autocomplete/$', EmployeeNameAutocomplete.as_view(), name='employee-autocomplete'),
    re_path(r'^client-autocomplete/$', ClientNameAutocomplete.as_view(), name='client-autocomplete'),
    re_path(r'^servic-autocomplete/$', ServiceNameAutocomplete.as_view(), name='service-autocomplete'),
]

