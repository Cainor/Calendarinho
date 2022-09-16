from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, MultiField, ButtonHolder, Submit, Div
import datetime
from dal import autocomplete
from django.forms import widgets
from .models import Comment,Service,Reports,Leave,Engagement,Client
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError



class EmployeeOverlapForm(forms.Form):
    Start_Date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date'
    }))
    End_Date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date'
    }))

class countEngDays(forms.Form):
    start_date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date(2020,1,1), widget=forms.TextInput(attrs={
        'type': 'date',
        'class': 'form-control'
    }))
    end_date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date',
        'class': 'form-control'
    }))

class Login_Form(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={'style': 'height: 15em;'}),
        }

class passwordforgetInitForm(forms.Form):
    email = forms.CharField(label='Email Address', max_length=100)

class passwordforgetEndForm(forms.Form):
    OTP = forms.CharField(label='One Time Password', max_length=100)
    new_Password = forms.CharField(widget=forms.PasswordInput())
    
    def clean_new_Password(self):
        data = self.cleaned_data['new_Password']
        password_validation.validate_password(data)

class uploadReportForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Div(
                Div(
                    'file',
                    css_class="col"
                ),
                Div(
                    'reportType',
                    css_class="col"
                ),Div(
                    'note',
                    css_class="col"
                ),
                css_class="row"
            ),
            ButtonHolder(
                Submit('submit', 'Upload', css_class='button')
            )
        )
    class Meta:
        model = Reports
        fields = ("file", "note","reportType",)
        widgets = {
            'file': forms.FileInput(attrs={'class':'col', 'required':'required'}),
            'reportType': forms.Select(attrs={'class':'col', 'required':'required'}),
            'note': forms.TextInput(attrs={'class':'col', 'accept': '.gpg'}),
        }
        
class DateInput(forms.DateInput):
    input_type = 'date'

class LeaveForm(forms.ModelForm): #Leave form for main page
    class Meta:
        model = Leave
        fields = ('Note','LeaveType','StartDate','EndDate')
        widgets = {
            'StartDate': DateInput(),
            'EndDate': DateInput(),
        }
    
    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")

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
            },),
            'StartDate': DateInput(),
            'EndDate': DateInput(),
        }
    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("StartDate") > cleaned_data.get("EndDate"):
            raise forms.ValidationError("Dates are incorrect")

class ClientForm(forms.ModelForm): #Leave form for main page
    class Meta:
        model = Client
        fields = '__all__'
