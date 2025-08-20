from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
import datetime
from collections import namedtuple
import numpy as np


class EmailField(models.CharField):
    def __init__(self, *args, **kwargs):
        super(EmailField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        return str(value).lower()

class CharField(models.Field):
    def __init__(self, *args, **kwargs):
        super(CharField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        return str(value).lower()

class CustomUser(AbstractUser):
    pass
    # add additional fields in here

    Manager = 'M'
    Employee = 'E'
    USER_TYPE_CHOICES = [
        (Manager, 'Manager'),
        (Employee, 'Employee'),
    ]
    user_type =  models.CharField(
        max_length = 1 ,
        choices=USER_TYPE_CHOICES,
        null=True,
    )

    # Authentication source tracking
    LOCAL = 'local'
    ACTIVE_DIRECTORY = 'ad'
    AUTH_SOURCE_CHOICES = [
        (LOCAL, 'Local'),
        (ACTIVE_DIRECTORY, 'Active Directory'),
    ]
    auth_source = models.CharField(
        max_length=20,
        choices=AUTH_SOURCE_CHOICES,
        default=LOCAL,
        help_text="Source of authentication for this user"
    )

    is_active = models.BooleanField(default=True)
    email = EmailField(max_length=50, unique=True)
    username = CharField(max_length=100, unique=True)

    date_quit = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.first_name + " " + self.last_name

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    

    def getAllLeaves(self):
        from CalendarinhoApp.models import Leave
        event_arr = []
        all_leaves = Leave.objects.filter(employee_id=self.id)
        for i in all_leaves:
            event_sub_arr = {}
            event_sub_arr['empName'] = self.first_name + " " + self.last_name 
            event_sub_arr['title'] = i.note + " - " + i.leave_type
            start_date = datetime.datetime.strptime(
                str(i.start_date), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.end_date + datetime.timedelta(days=1)), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            if i.leave_type == "Vacation":
                event_sub_arr['color'] = "#2C3E50"
            elif i.leave_type == "Training":
                event_sub_arr['color'] = "#2980B9"
            elif i.leave_type == "Work from Home":
                event_sub_arr['color'] = "#f39c12"
            else:
                event_sub_arr['color'] = "#2C3E50"
            event_arr.append(event_sub_arr)
        return event_arr

    def getAllEngagements(self):
        event_arr = []
        all_engagements = self.engagements.all().order_by('start_date')
        colors = ["#BD4932"]
        for i in all_engagements:
            event_sub_arr = {}
            event_sub_arr['name'] = i.name
            start_date = datetime.datetime.strptime(
                str(i.start_date), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.end_date  + datetime.timedelta(days=1)), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start_date'] = start_date
            event_sub_arr['end_date'] = end_date
            event_sub_arr['engID'] = i.id
            event_sub_arr['color'] = colors[0]
            event_sub_arr['service_type'] = i.service_type
            event_sub_arr['clientName'] = i.client
            event_arr.append(event_sub_arr)
        return event_arr

    # This method check if employee is availabile at a range of date
    def overlapCheck(self, StartDate, EndDate):
        from CalendarinhoApp.models import Leave, Engagement
        engs = Engagement.objects.filter(employees=self.id)
        leaves = Leave.objects.filter(employee_id=self.id)
        Range = namedtuple('Range', ['start', 'end'])
        start_date1 = datetime.datetime.strptime(str(StartDate), "%Y-%m-%d")
        end_date1 = datetime.datetime.strptime(str(EndDate), "%Y-%m-%d")
        Range1 = Range(start=start_date1, end=end_date1)
        event_dates = {"start_date": [], "end_date": []}
        for eng in engs:
            event_dates["start_date"].append(eng.start_date)
            event_dates["end_date"].append(eng.end_date)

        for lev in leaves:
            event_dates["start_date"].append(lev.start_date)
            event_dates["end_date"].append(lev.end_date)

        for i in range(len(event_dates["start_date"])):
            start_date2 = datetime.datetime.strptime(
                str(event_dates["start_date"][i]), "%Y-%m-%d")
            end_date2 = datetime.datetime.strptime(
                str(event_dates["end_date"][i]), "%Y-%m-%d")
            latestStart = max(start_date1, start_date2)
            earliestEnd = min(end_date1, end_date2)
            delta = (earliestEnd - latestStart).days + 1
            overlapDays = max(0, delta)
            if (overlapDays != 0):
                return True

    def dateInRange(self, date, fromDate, toDate):
        if fromDate <= datetime.date(date.year, date.month, date.day) <= toDate:
            return True
        else:
            return False

    def currentStatus(self):
        from CalendarinhoApp.models import Leave, Engagement
        todayDate = datetime.datetime.now()
        leaves = Leave.objects.filter(employee_id=self.id)
        for lev in leaves:
            if (self.dateInRange(todayDate, lev.start_date, lev.end_date)):
                return [lev.leave_type, lev.__str__(), lev.end_date]

        engs = Engagement.objects.filter(employees=self.id)
        for eng in engs:
            if (self.dateInRange(todayDate, eng.start_date, eng.end_date)):
                return ["Engaged", eng.__str__(), eng.end_date]

        return ["Available", "", "-"]

    def nextEvent(self):
        from CalendarinhoApp.models import Leave, Engagement
        eng = Engagement.objects.filter(employees=self.id).filter(
            start_date__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("start_date").first()
        lev = Leave.objects.filter(employee_id=self.id).filter(
            start_date__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("start_date").first()
        try:
            if eng and lev:
                if(eng.start_date > lev.start_date):
                    return [lev.__str__(), lev.start_date]
                else:
                    return [eng.__str__(), eng.start_date]
            elif eng is None and lev is None:
                return ["None", "-"]
            elif eng is None:
                return [lev.__str__(), lev.start_date]
            else:
                return [eng.__str__(), eng.start_date]
        except Exception:
            return ["None", "-"]

    def getManagers():
        return CustomUser.objects.filter(user_type="M")

    def getEmployees():
        return CustomUser.objects.filter(user_type="E")
    
    @classmethod
    def get_employee_statistics(cls):
        """Get comprehensive employee statistics"""
        today = datetime.date.today()
        employees = cls.objects.exclude(is_active=False)
        
        stats = {
            'total': employees.count(),
            'managers': employees.filter(user_type='M').count(),
            'employees': employees.filter(user_type='E').count(),
            'available': 0,
            'engaged': 0,
            'training': 0,
            'vacation': 0,
            'by_utilization': {
                'high': 0,  # >80%
                'medium': 0,  # 40-80%
                'low': 0   # <40%
            }
        }
        
        for emp in employees:
            status = emp.currentStatus()[0]
            if status == 'Available':
                stats['available'] += 1
            elif status == 'Engaged':
                stats['engaged'] += 1
            elif status == 'Training':
                stats['training'] += 1
            elif status == 'Vacation':
                stats['vacation'] += 1
            
            # Calculate utilization categorization
            utilization = emp.get_utilization_rate(30)
            if utilization >= 80:
                stats['by_utilization']['high'] += 1
            elif utilization >= 40:
                stats['by_utilization']['medium'] += 1
            else:
                stats['by_utilization']['low'] += 1
        
        return stats
    
    def get_status_display(self):
        """Get enhanced status display with better formatting"""
        empstat = self.currentStatus()
        status_type = empstat[0] if empstat else "Available"
        status_detail = empstat[1] if len(empstat) > 1 else ""
        
        if status_type == "Available":
            return {
                'type': 'Available',
                'label': 'Available',
                'class': 'success',
                'icon': '✓'
            }
        elif status_type == "Engaged":
            return {
                'type': 'Engaged',
                'label': f'Engaged: {status_detail}',
                'class': 'primary',
                'icon': '🔧'
            }
        elif status_type == "Training":
            return {
                'type': 'Training',
                'label': f'Training: {status_detail}',
                'class': 'info',
                'icon': '📚'
            }
        elif status_type == "Vacation":
            return {
                'type': 'Vacation',
                'label': f'Vacation: {status_detail}',
                'class': 'warning',
                'icon': '🏖️'
            }
        else:
            return {
                'type': status_type,
                'label': f'{status_type}: {status_detail}' if status_detail else status_type,
                'class': 'secondary',
                'icon': '❓'
            }
    
    def get_workload_summary(self):
        """Get comprehensive workload summary"""
        today = datetime.date.today()
        
        current_engagements = self.engagements.filter(
            start_date__lte=today, end_date__gte=today
        )
        
        upcoming_engagements = self.engagements.filter(
            start_date__gt=today
        ).order_by('start_date')[:3]  # Next 3 upcoming
        
        recent_leaves = self.get_recent_leaves(30)
        
        return {
            'current_engagements': list(current_engagements.values(
                'id', 'name', 'client__name', 'start_date', 'end_date'
            )),
            'upcoming_engagements': list(upcoming_engagements.values(
                'id', 'name', 'client__name', 'start_date', 'end_date'
            )),
            'recent_leaves': list(recent_leaves.values(
                'leave_type', 'start_date', 'end_date', 'note'
            )),
            'utilization_rate': self.get_utilization_rate(30),
            'total_engagements': self.engagements.count()
        }
    
    def get_availability_status(self, date=None):
        """Get detailed availability status for a specific date"""
        if date is None:
            date = datetime.date.today()
        
        # Check if employee has conflicts on this date
        has_conflict = self.overlapCheck(date, date)
        
        if not has_conflict:
            return {
                'available': True,
                'status': 'Available',
                'details': None
            }
        
        # Find what's causing the conflict
        from CalendarinhoApp.models import Leave, Engagement
        
        # Check leaves first
        leaves = Leave.objects.filter(
            employee_id=self.id,
            start_date__lte=date,
            end_date__gte=date
        )
        
        if leaves.exists():
            leave = leaves.first()
            return {
                'available': False,
                'status': leave.leave_type,
                'details': {
                    'type': 'leave',
                    'description': leave.note,
                    'start_date': leave.start_date,
                    'end_date': leave.end_date
                }
            }
        
        # Check engagements
        engagements = Engagement.objects.filter(
            employees=self.id,
            start_date__lte=date,
            end_date__gte=date
        )
        
        if engagements.exists():
            engagement = engagements.first()
            return {
                'available': False,
                'status': 'Engaged',
                'details': {
                    'type': 'engagement',
                    'name': engagement.name,
                    'client': engagement.client.name,
                    'start_date': engagement.start_date,
                    'end_date': engagement.end_date
                }
            }
        
        return {
            'available': False,
            'status': 'Unknown',
            'details': None
        }
        
    def countSrv(self, service_id):
        all_engagements = self.engagements.all()
        return all_engagements.filter(service_type=service_id).count()

    # function to calculate the number of days in each engagement
    def countEngDays(self, start_date, end_date):
        start_date = datetime.datetime.strptime(str(start_date), "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(str(end_date), "%Y-%m-%d").date()
        engs = self.engagements.all().filter(end_date__gte=start_date).filter(start_date__lte=end_date)
        noDays = 0
        for eng in engs:
            actStart = start_date if eng.start_date < start_date else eng.start_date
            actEnd = eng.end_date if eng.end_date < end_date else end_date

            countDays = np.busday_count(actStart, actEnd + datetime.timedelta(days=1), weekmask=settings.WORKING_DAYS)
            noDays += countDays

        return noDays
    
    def get_utilization_rate(self, days=30):
        """Calculate employee utilization rate over the last N days"""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        engaged_days = self.countEngDays(start_date, end_date)
        total_working_days = np.busday_count(start_date, end_date + datetime.timedelta(days=1), weekmask=settings.WORKING_DAYS)
        
        if total_working_days == 0:
            return 0
        return round((engaged_days / total_working_days) * 100, 2)
    
    def get_current_engagement(self):
        """Get the current active engagement for this employee"""
        from CalendarinhoApp.models import Engagement
        today = datetime.date.today()
        return Engagement.objects.filter(
            employees=self.id,
            start_date__lte=today,
            end_date__gte=today
        ).first()
    
    def get_upcoming_engagements(self, limit=5):
        """Get upcoming engagements for this employee"""
        from CalendarinhoApp.models import Engagement
        today = datetime.date.today()
        return Engagement.objects.filter(
            employees=self.id,
            start_date__gt=today
        ).order_by('start_date')[:limit]
    
    def get_recent_leaves(self, days=90):
        """Get recent leaves for this employee"""
        from CalendarinhoApp.models import Leave
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
        return Leave.objects.filter(
            employee_id=self.id,
            start_date__gte=cutoff_date
        ).order_by('-start_date')
    
    def has_conflicts(self, start_date, end_date):
        """Check if employee has any conflicts in the given date range"""
        return self.overlapCheck(start_date, end_date)
