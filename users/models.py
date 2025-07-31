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
