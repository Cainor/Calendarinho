from statistics import mode
from typing import Tuple
from django.db import models
from django.utils import timezone
import datetime, uuid
from collections import namedtuple
from users.models import CustomUser as Employee
from os.path import splitext
from django.core.exceptions import ValidationError


class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Client Name")
    acronym = models.CharField(max_length=10, verbose_name="Acronym")
    code = models.CharField(max_length=4, default='9999')

    class Meta:
        ordering = ['name']
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return str(self.name)

    def count_current_engagements(self):
        today = timezone.now().date()
        return self.engagements.filter(start_date__lte=today, end_date__gte=today).count()
    
    def count_working_employees(self):
        today = timezone.now().date()
        ongoing_engagements = self.engagements.filter(start_date__lte=today, end_date__gte=today)
        return sum(eng.working_employees() for eng in ongoing_engagements)



class Service(models.Model):
    name = models.CharField(max_length=200, verbose_name="Service Name")
    short_name = models.CharField(max_length=10, verbose_name="Service Shortname")

    def __str__(self):
        return str(self.name)



class Leave(models.Model):
    LEAVE_TYPES = (("Training", "Training"), ("Vacation", "Vacation"), ("Work from Home", "Work from Home"))
    employee = models.ForeignKey(Employee, verbose_name="Employee Name", on_delete=models.CASCADE)
    note = models.CharField(max_length=200)
    start_date = models.DateField('Start Date')
    end_date = models.DateField('End Date')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, default="Vacation", verbose_name="Leave Type")

    def __str__(self):
        return f"{self.leave_type} - {self.note}"
    


class OTP(models.Model):
    code = models.CharField(max_length=6, default='999999')
    email = models.EmailField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    tries = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.code)

    def now_diff(self):
        delta = timezone.now() - self.timestamp
        return delta.total_seconds()

    
class ProjectManager(models.Model):
    name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(max_length=200, blank=True)

    def __str__(self):
        return str(self.name)

class Engagement(models.Model):
    name = models.CharField(max_length=200, verbose_name="Engagement Name",
                               help_text="Developer Suggestion: Make sure to have a naming convention so you can automate this later")
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, verbose_name="Client Name", related_name="engagements")
    employees = models.ManyToManyField(
        Employee, blank=True, related_name="engagements")
    service_type = models.ForeignKey(
        Service, on_delete=models.PROTECT, verbose_name="Service Type")
    start_date = models.DateField('Start Date')
    end_date = models.DateField('End Date')
    scope = models.TextField(blank=True, verbose_name="Scope", help_text="Enter one domain/IP per line")
    project_manager = models.ForeignKey(
        ProjectManager, on_delete=models.PROTECT, related_name='engagements', verbose_name="Project Manager", null=True, blank=True)

    @classmethod
    def get_all_engagements(cls):
        event_arr = []
        all_events = cls.objects.all()
        colors = [
            "#990000", "#994C00", "#666600", "#336600", "#006600", "#006633",
            "#006666", "#003366", "#000066", "#330066", "#660066", "#660033", "#202020"
        ]
        for i in all_events:
            event_sub_arr = {}
            event_sub_arr['title'] = f"{i.name} -- {i.service_type}"
            start_date = i.start_date.strftime("%Y-%m-%d")
            end_date = (i.end_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            event_sub_arr['color'] = colors[i.id % len(colors)]
            event_arr.append(event_sub_arr)
        return event_arr

    def __str__(self):
        return f"{self.name} - {self.service_type}"

    def days_left_percentage(self):
        today = timezone.now().date()
        if self.start_date <= today <= self.end_date:
            days_left = (self.end_date - today).days
            total_days = (self.end_date - self.start_date).days
            try:
                percent = ((today - self.start_date).days / total_days) * 100
                return int(round(percent))
            except ZeroDivisionError:
                return 99
        return "Nope"

    def days_left_to_start(self):
        today = timezone.now().date()
        if today < self.start_date:
            days_left = (self.start_date - today).days
            return days_left
        return "Nope"
    
    def working_employees(self):
        return self.employees.count()


class Comment(models.Model):
    engagement = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='comments')
    body = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_on']

    def __str__(self):
        return f'Comment {self.body} by {self.user}'

class Report(models.Model):
    REPORT_TYPES = (("Draft", "Draft"), ("Final", "Final"), ("Verification", "Verification"))

    def set_filename(instance, filename):
        path = "Reports/"
        name, extension = splitext(filename)
        return f"{path}{instance.engagement.name}{extension}"

    def validate_file_extension(value):
        if not value.name.endswith('.gpg'):
            raise ValidationError(u'Extension must be gpg')

    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE)
    user = models.ForeignKey(Employee, on_delete=models.CASCADE)
    file = models.FileField(upload_to=set_filename, validators=[validate_file_extension])
    reference = models.CharField(max_length=36, default=uuid.uuid4)
    report_type = models.CharField(max_length=15, choices=REPORT_TYPES, default="Draft", verbose_name="Report Type")
    note = models.CharField(max_length=60, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        self.file.delete()
        super().delete(*args, **kwargs)