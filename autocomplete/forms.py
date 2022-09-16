from dal import autocomplete
from django import forms
from CalendarinhoApp.models import Engagement, Leave, Service

class EngagementForm(forms.ModelForm): #Engagement form for admin page

    class Meta:
        model = Engagement
        fields = ('EngName','CliName', 'Employees','projectManager','ServiceType','StartDate', 'EndDate', 'Scope')
        widgets = {
            'Employees': autocomplete.ModelSelect2Multiple(url='autocomplete:employee-autocomplete',
            attrs={
                'data-minimum-input-length': 2,
                },),
            'CliName': autocomplete.ModelSelect2(url='autocomplete:client-autocomplete',
            attrs={
                'data-minimum-input-length': 2,
                },),
            'projectManager':autocomplete.ModelSelect2(url='autocomplete:projectmanager-autocomplete',
            attrs={
                'data-minimum-input-length': 1,
            },)
        }
    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")


class LeaveForm(forms.ModelForm): #Leave form for admin page
    class Meta:
        model = Leave
        fields = ('Note','LeaveType','StartDate','EndDate')

    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")

class EmployeeCounter(autocomplete.FutureModelForm): #URL: /counterTable
    class Meta:
        model = Engagement
        fields = ('Employees', 'ServiceType',)
        widgets = {
            'Employees': autocomplete.ModelSelect2Multiple(url='autocomplete:employee-autocomplete', attrs={'class':' ml-1 mr-2'}),
            'ServiceType': autocomplete.ModelSelect2Multiple(url='autocomplete:service-autocomplete', attrs={'class':' ml-1 mr-2'}),
        }
    def __init__(self, *args, **kwargs):
        # first call parent's constructor
        super(EmployeeCounter, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        self.fields['ServiceType'].required = False

        