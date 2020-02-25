from django import forms
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