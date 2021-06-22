from django import forms
from crispy_forms.helper import FormHelper
import datetime
from .models import Comment,Service
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError



class EmployeeOverlapForm(forms.Form):
    Start_Date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date'
    }))
    End_Date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date'
    }))

class ResourceManagment(forms.Form):
    start_date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date',
        'class': 'form-control'
    }))
    end_date = forms.DateField(input_formats=['%Y-%m-%d'], initial=datetime.date.today, widget=forms.TextInput(attrs={
        'type': 'date',
        'class': 'form-control'
    }))
    servList = forms.ChoiceField(label='Service',widget=forms.Select(attrs={'class': 'form-control'}))


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servList'].choices= [(serv.id, serv.serviceName) for serv in Service.objects.all()]

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if end_date < start_date:
            raise forms.ValidationError("End date should be greater than start date.")

class Login_Form(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={'style': 'height: 5em;'}),
        }

class passwordforgetInitForm(forms.Form):
    email = forms.CharField(label='Email Address', max_length=100)

class passwordforgetEndForm(forms.Form):
    OTP = forms.CharField(label='One Time Password', max_length=100)
    new_Password = forms.CharField(widget=forms.PasswordInput())
    
    def clean_new_Password(self):
        data = self.cleaned_data['new_Password']
        password_validation.validate_password(data)

