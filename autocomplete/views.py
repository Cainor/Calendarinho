from unicodedata import name
from django.shortcuts import render

from dal import autocomplete
from CalendarinhoApp.models import Employee, Client, Service, ProjectManager
from django.db.models import Q 

class EmployeeNameAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Employee.objects.none()

        AllEmps = Employee.objects.all()

        if self.q:
            for term in self.q.split():
                AllEmps = AllEmps.filter(Q(first_name__icontains = term) | Q(last_name__icontains = term)).order_by("first_name")
        return AllEmps

class ClientNameAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Client.objects.none()

        AllCli = Client.objects.all()

        if self.q:
            for term in self.q.split():
                AllCli = AllCli.filter(Q(CliName__icontains = term) | Q(CliShort__icontains = term)).order_by("CliName")
        return AllCli

class ServiceNameAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Service.objects.none()

        AllSrv = Service.objects.all()

        if self.q:
            for term in self.q.split():
                AllSrv = AllSrv.filter(Q(serviceName__icontains = term) | Q(serviceShort__icontains = term)).order_by("serviceName")
        return AllSrv

class ProjectManagerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return ProjectManager.objects.none()

        AllprjManagers = ProjectManager.objects.all()

        if self.q:
            for term in self.q.split():
                AllprjManagers = AllprjManagers.filter(Q(name__icontains = term) | Q(name__icontains = term)).order_by("name")
        return AllprjManagers