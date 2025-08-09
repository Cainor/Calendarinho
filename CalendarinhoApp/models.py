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
    acronym = models.CharField(max_length=50, verbose_name="Acronym")
    code = models.CharField(max_length=50, default='9999')

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
        """Count employees currently working on client engagements (optimized)"""
        today = timezone.now().date()
        ongoing_engagements = self.engagements.filter(start_date__lte=today, end_date__gte=today)
        return sum(eng.working_employees() for eng in ongoing_engagements)
    
    def get_engagement_history_summary(self):
        """Get summary of engagement history for this client"""
        today = timezone.now().date()
        engagements = self.engagements.all()
        
        summary = {
            'total_engagements': engagements.count(),
            'completed_engagements': engagements.filter(end_date__lt=today).count(),
            'ongoing_engagements': engagements.filter(start_date__lte=today, end_date__gte=today).count(),
            'upcoming_engagements': engagements.filter(start_date__gt=today).count(),
            'total_duration_days': sum((eng.end_date - eng.start_date).days + 1 for eng in engagements),
        }
        
        # Calculate average engagement duration
        if summary['total_engagements'] > 0:
            summary['avg_duration_days'] = round(summary['total_duration_days'] / summary['total_engagements'], 1)
        else:
            summary['avg_duration_days'] = 0
        
        # Find first and last engagement dates
        first_engagement = engagements.order_by('start_date').first()
        last_engagement = engagements.order_by('-end_date').first()
        
        summary['first_engagement_date'] = first_engagement.start_date if first_engagement else None
        summary['last_engagement_date'] = last_engagement.end_date if last_engagement else None
        
        return summary
    
    def get_activity_score(self):
        """Calculate a client activity score based on recent engagement activity"""
        today = timezone.now().date()
        
        # Weight recent activity more heavily
        score = 0
        
        # Current engagements (highest weight)
        current_count = self.count_current_engagements()
        score += current_count * 10
        
        # Recent engagements (last 90 days)
        recent_engagements = self.engagements.filter(
            end_date__gte=today - timezone.timedelta(days=90)
        ).count()
        score += recent_engagements * 5
        
        # Upcoming engagements (next 90 days)
        upcoming_engagements = self.engagements.filter(
            start_date__gt=today,
            start_date__lte=today + timezone.timedelta(days=90)
        ).count()
        score += upcoming_engagements * 3
        
        return score

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
    
    @classmethod
    def get_ongoing_engagements(cls):
        """Get all currently ongoing engagements with optimized queries"""
        today = timezone.now().date()
        return cls.objects.select_related('client', 'service_type').prefetch_related(
            'employees', 'vulnerabilities'
        ).filter(
            start_date__lte=today,
            end_date__gte=today
        )
    
    @classmethod
    def get_upcoming_engagements(cls, days=30):
        """Get engagements starting within the next N days"""
        today = timezone.now().date()
        future_date = today + datetime.timedelta(days=days)
        return cls.objects.select_related('client', 'service_type').prefetch_related(
            'employees'
        ).filter(
            start_date__gt=today,
            start_date__lte=future_date
        ).order_by('start_date')
    
    def get_team_utilization(self):
        """Calculate the current team utilization for this engagement"""
        today = timezone.now().date()
        if not (self.start_date <= today <= self.end_date):
            return 0
        
        total_employees = self.employees.count()
        if total_employees == 0:
            return 0
        
        # Count employees who are not on leave today
        available_employees = 0
        for emp in self.employees.all():
            if not emp.overlapCheck(today, today):  # No overlap means available
                available_employees += 1
        
        return round((available_employees / total_employees) * 100, 2)
    
    def get_status_display(self):
        """Get human-readable status for the engagement"""
        today = timezone.now().date()
        if self.start_date > today:
            days_until = (self.start_date - today).days
            return f"Starts in {days_until} days"
        elif self.start_date <= today <= self.end_date:
            days_left = (self.end_date - today).days
            if days_left == 0:
                return "Ends today"
            elif days_left == 1:
                return "Ends tomorrow"
            else:
                return f"{days_left} days remaining"
        else:
            days_ago = (today - self.end_date).days
            return f"Completed {days_ago} days ago"

    def can_be_edited_by(self, user):
        """Check if user has permission to edit this engagement"""
        if user.is_superuser or user.user_type == 'M':
            return True
        
        if user in self.employees.all():
            return True
        
        return False

    def get_editable_fields(self, user):
        """Get list of fields that can be edited by the given user"""
        if not self.can_be_edited_by(user):
            return []
        
        editable_fields = ['name', 'start_date', 'end_date', 'scope']
        
        # Only managers can edit critical engagement details
        if not (user.is_superuser or user.user_type == 'M'):
            # Regular team members have limited editing capabilities
            editable_fields = ['scope']  # Only scope can be edited by team members
        
        return editable_fields


class Comment(models.Model):
    engagement = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='comments')
    body = models.TextField()
    mentioned_users = models.ManyToManyField(
        Employee, blank=True, related_name='mentioned_in_comments')
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

    def can_be_edited_by(self, user):
        """Check if user has permission to edit this vulnerability"""
        if user.is_superuser or user.user_type == 'M':
            return True
        
        if user == self.created_by:
            return True
        
        if user in self.engagement.employees.all():
            return True
        
        return False

    def get_editable_fields(self, user):
        """Get list of fields that can be edited by the given user"""
        if not self.can_be_edited_by(user):
            return []
        
        editable_fields = ['title', 'description', 'severity', 'status']
        
        # Regular users might have restrictions on certain fields
        if not (user.is_superuser or user.user_type == 'M'):
            # Non-managers can edit all fields for now
            # Future enhancement: add field-level restrictions
            pass
        
        return editable_fields

    def validate_field_update(self, field_name, new_value):
        """Validate a field update before saving"""
        errors = []
        
        if field_name == 'title':
            if not new_value or len(new_value.strip()) < 3:
                errors.append("Title must be at least 3 characters long")
            elif len(new_value) > 200:
                errors.append("Title cannot exceed 200 characters")
        
        elif field_name == 'description':
            if not new_value or len(new_value.strip()) < 10:
                errors.append("Description must be at least 10 characters long")
        
        elif field_name == 'severity':
            valid_severities = [choice[0] for choice in self.SEVERITY_CHOICES]
            if new_value not in valid_severities:
                errors.append(f"Invalid severity. Must be one of: {', '.join(valid_severities)}")
        
        elif field_name == 'status':
            valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
            if new_value not in valid_statuses:
                errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        return errors


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