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

