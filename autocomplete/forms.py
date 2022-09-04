from dal import autocomplete
from django import forms
from CalendarinhoApp.models import Employee, Engagement, Leave, Service
from users.models import CustomUser



class EngagementForm(forms.ModelForm):

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
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('__all__')
        widgets = {
            'skilledEmp': autocomplete.ModelSelect2Multiple(url='autocomplete:employee-autocomplete',
            attrs={
                'data-minimum-input-length': 2,
                },)
        }


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ('Note','LeaveType','StartDate','EndDate')
        widgets = {
            'emp': autocomplete.ModelSelect2(url='autocomplete:employee-autocomplete',
            attrs={
                'data-minimum-input-length': 2,
                },)
        }
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")

class EmployeeCounter(autocomplete.FutureModelForm):
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

        