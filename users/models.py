from django.contrib.auth.models import AbstractUser
from django.db import models
import datetime
from collections import namedtuple

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

    USER_LEVEL_CHOICES = [
        ('1', 'Analyst'),
        ('2', 'Consultant'),
        ('3', 'Senior Consultant'),
        ('4', 'Managing Consultant'),
    ]
    user_level = models.CharField(
        max_length = 1 ,
        choices=USER_LEVEL_CHOICES,
        null=True,
    )

    is_active = models.BooleanField(default=True)
    email = EmailField(max_length=50, unique=True)
    username = CharField(max_length=100, unique=True)

    def __str__(self):
        return self.first_name + " " + self.last_name

    

    def getAllLeaves(self):
        from CalendarinhoApp.models import Leave
        event_arr = []
        all_leaves = Leave.objects.filter(emp_id=self.id)
        colors = ["#2C3E50", "#2980B9"]
        for i in all_leaves:
            event_sub_arr = {}
            event_sub_arr['empName'] = self.first_name + " " + self.last_name 
            event_sub_arr['title'] = i.Note + " -- " + i.LeaveType
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate + datetime.timedelta(days=1)), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            event_sub_arr['color'] = colors[0] if i.LeaveType == "Vacation" else colors[1]
            event_arr.append(event_sub_arr)
        return event_arr

    def getAllEngagements(self):
        event_arr = []
        all_engagements = self.Engagements.all().order_by('StartDate')
        colors = ["#BD4932"]
        for i in all_engagements:
            event_sub_arr = {}
            event_sub_arr['name'] = i.EngName
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate  + datetime.timedelta(days=1)), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['startDate'] = start_date
            event_sub_arr['endDate'] = end_date
            event_sub_arr['engID'] = i.id
            event_sub_arr['color'] = colors[0]
            event_sub_arr['serviceType'] = i.ServiceType
            event_sub_arr['clientName'] = i.CliName
            event_arr.append(event_sub_arr)
        return event_arr

    # This method check if employee is availabile at a range of date
    def overlapCheck(self, StartDate, EndDate):
        from CalendarinhoApp.models import Leave, Engagement
        engs = Engagement.objects.filter(Employees=self.id)
        leaves = Leave.objects.filter(emp_id=self.id)
        Range = namedtuple('Range', ['start', 'end'])
        start_date1 = datetime.datetime.strptime(str(StartDate), "%Y-%m-%d")
        end_date1 = datetime.datetime.strptime(str(EndDate), "%Y-%m-%d")
        Range1 = Range(start=start_date1, end=end_date1)
        event_dates = {"start_date": [], "end_date": []}
        for eng in engs:
            event_dates["start_date"].append(eng.StartDate)
            event_dates["end_date"].append(eng.EndDate)

        for lev in leaves:
            event_dates["start_date"].append(lev.StartDate)
            event_dates["end_date"].append(lev.EndDate)

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
        leaves = Leave.objects.filter(emp_id=self.id)
        for lev in leaves:
            if (self.dateInRange(todayDate, lev.StartDate, lev.EndDate)):
                return [lev.LeaveType, lev.__str__(), lev.EndDate]

        engs = Engagement.objects.filter(Employees=self.id)
        for eng in engs:
            if (self.dateInRange(todayDate, eng.StartDate, eng.EndDate)):
                return ["Engaged", eng.__str__(), eng.EndDate]

        return ["Available", "", "-"]

    def nextEvent(self):
        from CalendarinhoApp.models import Leave, Engagement
        eng = Engagement.objects.filter(Employees=self.id).filter(
            StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("StartDate").first()
        lev = Leave.objects.filter(emp_id=self.id).filter(
            StartDate__gt=datetime.datetime.now().strftime("%Y-%m-%d")).order_by("StartDate").first()
        try:
            if(eng.StartDate > lev.StartDate):
                return [lev.__str__(), lev.StartDate]
            else:
                return [eng.__str__(), eng.StartDate]
        except:
            if(eng == None and lev == None):
                return["None", "-"]
            elif(eng == None):
                return [lev.__str__(), lev.StartDate]
            else:
                return [eng.__str__(), eng.StartDate]

    def getManagers():
        return CustomUser.objects.filter(user_type="M")

    def getEmployees():
        return CustomUser.objects.filter(user_type="E")
        
    def countSrv(self,service_id):
        result = 0
        all_engagements = self.Engagements.all()
        
        result = all_engagements.filter(ServiceType = service_id).count()
        return result
    
    def levelToText(self):
        if(self.user_level == '1'):
            return "Analyst"
        elif(self.user_level == '2'):
            return "Consultant"
        elif(self.user_level == '3'):
            return "Senior Consultant"
        elif(self.user_level == '4'):
            return "Managing Consultant"