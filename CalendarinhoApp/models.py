from statistics import mode
from typing import Tuple
from django.db import models
from django.utils import timezone
from django.db.models import Count, Q, Case, When, IntegerField
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

    def get_vulnerability_summary(self):
        """Get vulnerability summary for all client engagements using optimized database queries"""
        # Use aggregation to count vulnerabilities in a single query
        summary_data = self.engagements.aggregate(
            critical_open=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Critical', vulnerabilities__status='Open')),
            high_open=Count('vulnerabilities', filter=Q(vulnerabilities__severity='High', vulnerabilities__status='Open')),
            medium_open=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Medium', vulnerabilities__status='Open')),
            low_open=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Low', vulnerabilities__status='Open')),
            critical_fixed=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Critical', vulnerabilities__status='Fixed')),
            high_fixed=Count('vulnerabilities', filter=Q(vulnerabilities__severity='High', vulnerabilities__status='Fixed')),
            medium_fixed=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Medium', vulnerabilities__status='Fixed')),
            low_fixed=Count('vulnerabilities', filter=Q(vulnerabilities__severity='Low', vulnerabilities__status='Fixed')),
        )
        
        # Calculate totals
        summary_data['total_open'] = (
            summary_data['critical_open'] + summary_data['high_open'] + 
            summary_data['medium_open'] + summary_data['low_open']
        )
        summary_data['total_fixed'] = (
            summary_data['critical_fixed'] + summary_data['high_fixed'] + 
            summary_data['medium_fixed'] + summary_data['low_fixed']
        )
        
        # Count engagements with open vulnerabilities
        summary_data['engagements_with_vulnerabilities'] = self.engagements.filter(
            vulnerabilities__status='Open'
        ).distinct().count()
        
        return summary_data


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

    def get_vulnerability_summary(self):
        """Get vulnerability summary for this engagement using optimized database queries"""
        # Use aggregation to count vulnerabilities in a single query
        summary_data = self.vulnerabilities.aggregate(
            critical_open=Count('id', filter=Q(severity='Critical', status='Open')),
            high_open=Count('id', filter=Q(severity='High', status='Open')),
            medium_open=Count('id', filter=Q(severity='Medium', status='Open')),
            low_open=Count('id', filter=Q(severity='Low', status='Open')),
            critical_fixed=Count('id', filter=Q(severity='Critical', status='Fixed')),
            high_fixed=Count('id', filter=Q(severity='High', status='Fixed')),
            medium_fixed=Count('id', filter=Q(severity='Medium', status='Fixed')),
            low_fixed=Count('id', filter=Q(severity='Low', status='Fixed')),
        )
        
        # Calculate totals
        summary_data['total_open'] = (
            summary_data['critical_open'] + summary_data['high_open'] + 
            summary_data['medium_open'] + summary_data['low_open']
        )
        summary_data['total_fixed'] = (
            summary_data['critical_fixed'] + summary_data['high_fixed'] + 
            summary_data['medium_fixed'] + summary_data['low_fixed']
        )
        
        return summary_data

    def has_remaining_vulnerabilities(self):
        """Check if engagement has any open vulnerabilities - optimized version"""
        return self.vulnerabilities.filter(status='Open').exists()

    def get_vulnerability_risk_score(self):
        """Calculate a risk score based on vulnerability severity and count"""
        summary = self.get_vulnerability_summary()
        # Weight: Critical=10, High=7, Medium=4, Low=1
        risk_score = (
            summary['critical_open'] * 10 +
            summary['high_open'] * 7 +
            summary['medium_open'] * 4 +
            summary['low_open'] * 1
        )
        return risk_score

    def get_vulnerability_remediation_rate(self):
        """Calculate the percentage of vulnerabilities that have been fixed"""
        summary = self.get_vulnerability_summary()
        total_vulns = summary['total_open'] + summary['total_fixed']
        if total_vulns == 0:
            return 100  # No vulnerabilities means 100% remediation
        return round((summary['total_fixed'] / total_vulns) * 100, 2)


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


class Vulnerability(models.Model):
    SEVERITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Fixed', 'Fixed'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Vulnerability Title")
    description = models.TextField(verbose_name="Description")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='Medium')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Open')
    report = models.ForeignKey('Report', on_delete=models.CASCADE, related_name='vulnerabilities', null=True, blank=True)
    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name='vulnerabilities')
    created_by = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='created_vulnerabilities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fixed_at = models.DateTimeField(null=True, blank=True)
    fixed_by = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='fixed_vulnerabilities', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']  # We'll handle severity ordering in views
        verbose_name = "Vulnerability"
        verbose_name_plural = "Vulnerabilities"
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['engagement', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.severity} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Update fixed_at timestamp when status changes to Fixed
        if self.status == 'Fixed' and not self.fixed_at:
            self.fixed_at = timezone.now()
        elif self.status == 'Open':
            self.fixed_at = None
            self.fixed_by = None
        super().save(*args, **kwargs)
    
    def get_severity_color(self):
        """Get Bootstrap color class for severity"""
        colors = {
            'Critical': 'danger',
            'High': 'warning',
            'Medium': 'info',
            'Low': 'success'
        }
        return colors.get(self.severity, 'secondary')
    
    def get_severity_icon(self):
        """Get icon for severity level"""
        icons = {
            'Critical': '🔴',
            'High': '🟠',
            'Medium': '🟡',
            'Low': '🟢'
        }
        return icons.get(self.severity, '⚪')

    def get_severity_weight(self):
        """Get numeric weight for severity (useful for calculations)"""
        weights = {
            'Critical': 10,
            'High': 7,
            'Medium': 4,
            'Low': 1
        }
        return weights.get(self.severity, 0)

    def days_to_fix(self):
        """Calculate days taken to fix vulnerability"""
        if self.status == 'Fixed' and self.fixed_at:
            delta = self.fixed_at.date() - self.created_at.date()
            return delta.days
        return None

    def is_overdue(self, sla_days=None):
        """Check if vulnerability is overdue based on SLA"""
        if self.status == 'Fixed':
            return False
        
        if sla_days is None:
            # Default SLA based on severity
            sla_mapping = {
                'Critical': 7,
                'High': 30,
                'Medium': 90,
                'Low': 180
            }
            sla_days = sla_mapping.get(self.severity, 90)
        
        days_open = (timezone.now().date() - self.created_at.date()).days
        return days_open > sla_days


class Report(models.Model):
    REPORT_TYPES = (("Draft", "Draft"), ("Final", "Final"), ("Verification", "Verification"))

    def set_filename(instance, filename):
        path = "Reports/"
        name, extension = splitext(filename)
        return f"{path}{instance.engagement.name}{extension}"

    def validate_file_extension(value):
        if not value.name.endswith('.gpg'):
            # raise ValidationError(u'Extension must be gpg')
            pass

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
    
    def get_vulnerability_summary(self):
        """Get vulnerability summary for this report using optimized database queries"""
        # Use aggregation to count vulnerabilities in a single query
        summary_data = self.vulnerabilities.aggregate(
            critical_open=Count('id', filter=Q(severity='Critical', status='Open')),
            high_open=Count('id', filter=Q(severity='High', status='Open')),
            medium_open=Count('id', filter=Q(severity='Medium', status='Open')),
            low_open=Count('id', filter=Q(severity='Low', status='Open')),
            critical_fixed=Count('id', filter=Q(severity='Critical', status='Fixed')),
            high_fixed=Count('id', filter=Q(severity='High', status='Fixed')),
            medium_fixed=Count('id', filter=Q(severity='Medium', status='Fixed')),
            low_fixed=Count('id', filter=Q(severity='Low', status='Fixed')),
        )
        
        # Calculate totals
        summary_data['total_open'] = (
            summary_data['critical_open'] + summary_data['high_open'] + 
            summary_data['medium_open'] + summary_data['low_open']
        )
        summary_data['total_fixed'] = (
            summary_data['critical_fixed'] + summary_data['high_fixed'] + 
            summary_data['medium_fixed'] + summary_data['low_fixed']
        )
        
        return summary_data