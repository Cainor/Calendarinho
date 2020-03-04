from django import forms
from crispy_forms.helper import FormHelper
import datetime

class EmployeeOverlapForm(forms.Form):
    Start_Date = forms.DateField(input_formats=['%Y-%m-%d'] ,initial=datetime.date.today, widget=forms.TextInput(attrs=
                                {
                                    'type':'date'
                                }))
    End_Date = forms.DateField(input_formats=['%Y-%m-%d'] ,initial=datetime.date.today, widget=forms.TextInput(attrs=
                                {
                                    'type':'date'
                                }))

class Login_Form(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())