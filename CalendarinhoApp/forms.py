from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, MultiField, ButtonHolder, Submit, Div, HTML
import datetime
from dal import autocomplete
from django.forms import widgets
from .models import Comment, Service, Report, Leave, Engagement, Client, Vulnerability
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

class VulnerabilityCountForm(forms.Form):
    # New vulnerabilities found in this report
    critical_new = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    high_new = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    medium_new = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    low_new = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    
    # Vulnerabilities fixed in this report
    critical_fixed = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    high_fixed = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    medium_fixed = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )
    low_fixed = forms.IntegerField(
        min_value=0, 
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control text-center',
            'style': 'width: 80px;',
            'placeholder': '0'
        })
    )

class uploadReportForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            # Report upload section only
            Div(
                Div('file', css_class="col-md-4"),
                Div('report_type', css_class="col-md-4"),
                Div('note', css_class="col-md-4"),
                css_class="row mb-4"
            ),
            ButtonHolder(
                Submit('submit', 'Upload Report', css_class='btn btn-primary px-4')
            )
        )

    def generate_vulnerability_titles(self, severity, count, existing_count=0):
        """Generate vulnerability titles based on severity and count pattern"""
        severity_abbrev = {
            'Critical': 'c',
            'High': 'h', 
            'Medium': 'm',
            'Low': 'l'
        }
        
        titles = []
        abbrev = severity_abbrev.get(severity, severity.lower()[0])
        
        for i in range(count):
            title = f"{abbrev}{existing_count + i + 1}"
            titles.append(title)
        
        return titles
    
    def get_vulnerability_title_preview(self):
        """Generate a preview of vulnerability titles that will be created"""
        preview = []
        
        # Get existing vulnerability counts for pattern generation
        existing_counts = {
            'Critical': 0,
            'High': 0,
            'Medium': 0,
            'Low': 0
        }
        
        # Add new vulnerabilities to preview
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            count = self.cleaned_data.get(f'{severity.lower()}_new', 0)
            if count > 0:
                titles = self.generate_vulnerability_titles(
                    severity, 
                    count, 
                    existing_counts[severity]
                )
                preview.extend(titles)
                existing_counts[severity] += count
        
        return ' '.join(preview) if preview else "No vulnerabilities"

    class Meta:
        model = Report
        fields = ("file", "note", "report_type",)
        widgets = {
            'file': forms.FileInput(attrs={'class':'form-control', 'required':'required'}),
            'report_type': forms.Select(attrs={'class':'form-control', 'required':'required'}),
            'note': forms.TextInput(attrs={'class':'form-control'}),
        }
        
class DateInput(forms.DateInput):
    input_type = 'date'

class LeaveForm(forms.ModelForm): #Leave form for main page
    class Meta:
        model = Leave
        fields = ('note','leave_type','start_date','end_date')
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
    leave_type = forms.ChoiceField(choices=Leave.LEAVE_TYPES)
    
    def clean(self): #Validation
        cleaned_data = super().clean()
        if cleaned_data.get("start_date") > cleaned_data.get("end_date"):
            raise forms.ValidationError("Dates are incorrect")

class EngagementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'engagement-form'
        self.helper.layout = Layout(
            Div(
                Div(
                    'name',
                    css_class='form-group'
                ),
                css_class='mb-4'
            ),
            Div(
                Div(
                    'client',
                    css_class=' col-md-6'
                ),
                Div(
                    'project_manager',
                    css_class=' col-md-6'
                ),
                css_class='row'
            ),
            Div(
                Div(
                    'employees',
                    css_class='form-group'
                ),
                css_class='mb-4'
            ),
            Div(
                Div(
                    'service_type',
                    css_class='form-group col-md-4'
                ),
                Div(
                    'start_date',
                    css_class='form-group col-md-4'
                ),
                Div(
                    'end_date',
                    css_class='form-group col-md-4'
                ),
                css_class='row mb-4'
            ),
            Div(
                Div(
                    'scope',
                    css_class='form-group'
                ),
                css_class='mb-4'
            ),
            Div(
                Submit('submit', 'Create Engagement', css_class='btn btn-primary px-4'),
                css_class='text-left'
            )
        )

    class Meta:
        model = Engagement
        fields = ('name', 'client', 'employees', 'project_manager', 'service_type', 'start_date', 'end_date', 'scope')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter engagement name'
            }),
            'employees': autocomplete.ModelSelect2Multiple(
                url='autocomplete:employee-autocomplete',
                attrs={
                    'data-minimum-input-length': 0,
                    'class': 'form-control',
                    'data-placeholder': 'Select employees'
                }
            ),
            'client': autocomplete.ModelSelect2(
                url='autocomplete:client-autocomplete',
                attrs={
                    'data-minimum-input-length': 0,
                    'class': 'form-control',
                    'data-placeholder': 'Select client',
                    'required': True
                }
            ),
            'project_manager': autocomplete.ModelSelect2(
                url='autocomplete:projectmanager-autocomplete',
                attrs={
                    'data-minimum-input-length': 0,
                    'class': 'form-control',
                    'data-placeholder': 'Select project manager'
                }
            ),
            'service_type': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': '--------'
            }),
            'start_date': DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'mm/dd/yyyy'
            }),
            'end_date': DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'mm/dd/yyyy'
            }),
            'scope': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter engagement scope',
                'help_text': 'Enter one domain/IP per line'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ('name', 'short_name')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter service name'
            }),
            'short_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short name (max 10 chars)'
            })
        }

class ClientForm(forms.ModelForm): #Leave form for main page
    class Meta:
        model = Client
        fields = '__all__'
