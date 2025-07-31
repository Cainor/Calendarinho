from dal import autocomplete
from django import forms
from CalendarinhoApp.models import Engagement, Leave, Service

class EngagementForm(forms.ModelForm): #Engagement form for admin page

    class Meta:
        model = Engagement
        fields = ('name', 'client', 'employees', 'project_manager', 'service_type', 'start_date', 'end_date', 'scope')
        widgets = {
            'employees': autocomplete.ModelSelect2Multiple(url='autocomplete:employee-autocomplete',
            attrs={
                'data-minimum-input-length': 0,
                },),
            'client': autocomplete.ModelSelect2(url='autocomplete:client-autocomplete',
            attrs={
                'data-minimum-input-length': 0,
                },),
            'project_manager':autocomplete.ModelSelect2(url='autocomplete:projectmanager-autocomplete',
            attrs={
                'data-minimum-input-length': 0,
            },)
        }
    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("start_date") and cleaned_data.get("end_date") and cleaned_data.get("start_date") > cleaned_data.get("end_date"):
            raise forms.ValidationError("Dates are incorrect")


class LeaveForm(forms.ModelForm): #Leave form for admin page
    class Meta:
        model = Leave
        fields = ('note', 'leave_type', 'start_date', 'end_date')

    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("start_date") and cleaned_data.get("end_date") and cleaned_data.get("start_date") > cleaned_data.get("end_date"):
            raise forms.ValidationError("Dates are incorrect")

class EmployeeCounter(autocomplete.FutureModelForm): #URL: /counterTable
    class Meta:
        model = Engagement
        fields = ('employees', 'service_type',)
        widgets = {
            'employees': autocomplete.ModelSelect2Multiple(url='autocomplete:employee-autocomplete', attrs={'class':' ml-1 mr-2', 'data-placeholder':'All Users'}),
            'service_type': autocomplete.ModelSelect2Multiple(url='autocomplete:service-autocomplete', attrs={'class':' ml-1 mr-2', 'data-placeholder':'All Services'}),
        }
    def __init__(self, *args, **kwargs):
        # first call parent's constructor
        super(EmployeeCounter, self).__init__(*args, **kwargs)  
        # there's a `fields` property now
        self.fields['service_type'].required = False

        