from statistics import mode
from typing import Tuple
from django.db import models
import datetime, uuid
from collections import namedtuple
from users.models import CustomUser as Employee
from os.path import splitext
from django.core.exceptions import ValidationError


class Client(models.Model):
    CliName = models.CharField(max_length=200, verbose_name="Client Name")
    CliShort = models.CharField(max_length=10, verbose_name="Acronym")
    CliCode = models.CharField(max_length=4, default='9999')

    class Meta:
        ordering = ['CliName']

    def __str__(self):
        return str(self.CliName)

    def countCurrentEng(self):
        OngoingCount = self.Engagements.filter(StartDate__lte=str(datetime.date.today())).filter(EndDate__gte=str(datetime.date.today())).count()
        return int(OngoingCount)
    
    def countWorkingEmp(self):
        OngoingEng = self.Engagements.filter(StartDate__lte=str(datetime.date.today())).filter(EndDate__gte=str(datetime.date.today()))
        count = 0
        for eng in OngoingEng:
            count += eng.workingEmp()
        return count



class Service(models.Model):
    serviceName = models.CharField(max_length=200, verbose_name="Service Name")
    serviceShort = models.CharField(
        max_length=10, verbose_name="Service Shortname")

    def __str__(self):
        return str(self.serviceName)



class Leave(models.Model):
    emp = models.ForeignKey(Employee, verbose_name="Employee Name",on_delete=models.CASCADE)
    Note = models.CharField(max_length=200)
    StartDate = models.DateField('Start Date')
    EndDate = models.DateField('End Date')
    Types = (("Training", "Training"), ("Vacation", "Vacation"))
    LeaveType = models.CharField(
        max_length=8, choices=Types, default="Vacation", verbose_name="Leave Type")

    def __str__(self):
        return str(self.LeaveType) + " - " + str(self.Note)
    


class OTP(models.Model):
    OTP = models.CharField(max_length=6, default='999999')
    Email = models.CharField(max_length=50)
    Timestamp = models.DateTimeField(auto_now_add=True)
    Tries = models.CharField(max_length=1, default='0')

    def __str__(self):
        return str(self.OTP)

    def now_diff(self):
        delta = datetime.datetime.now() - self.Timestamp
        return delta.total_seconds()

    
class ProjectManager(models.Model):
    name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return str(self.name)

class Engagement(models.Model):
    EngName = models.CharField(max_length=200, verbose_name="Engagement Name",
                               help_text="Developer Suggestion: Make sure to have a naming convention so you can automate this later")
    CliName = models.ForeignKey(
        Client, on_delete=models.PROTECT, verbose_name="Client Name", related_name="Engagements")
    Employees = models.ManyToManyField(
        Employee, blank=True, related_name="Engagements")
    ServiceType = models.ForeignKey(
        Service, on_delete=models.PROTECT, verbose_name="Service Type")
    StartDate = models.DateField('Start Date')
    EndDate = models.DateField('End Date')
    Scope = models.TextField(blank=False, verbose_name="Scope", help_text="Enter one domain/IP per line")
    projectManager = models.ForeignKey(
        ProjectManager, on_delete=models.PROTECT, related_name='engs', null=True, blank=True)

    def getAllEngs():
        event_arr = []
        all_events = Engagement.objects.all()
        colors = ["#990000", "#994C00", "#666600",
                  "#336600", "#006600", "#006633",
                  "#006666", "#003366", "#000066",
                  "#330066", "#660066", "#660033",
                  "#202020"]
        for i in all_events:
            event_sub_arr = {}
            event_sub_arr['title'] = i.EngName + " -- " + str(i.ServiceType)
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate + datetime.timedelta(days=1)), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            event_sub_arr['color'] = colors[i.id % len(colors)]
            event_arr.append(event_sub_arr)
        return event_arr

    def __str__(self):
        return str(self.EngName) + " - " + str(self.ServiceType)

    def daysLeftPrecentage(self):
        todayDatetiem = datetime.date.today()
        todayDate = datetime.date(
            todayDatetiem.year, todayDatetiem.month, todayDatetiem.day)
        if (todayDate >= self.StartDate and todayDate <= self.EndDate):
            daysLeft = todayDate - self.EndDate
            totalDays = self.EndDate - self.StartDate
            try:
                precent = (daysLeft / totalDays) * 100
                return int("{:2.0f}".format(precent+100))
            except ZeroDivisionError:
                # If the engagement is only 1 day, this will be triggered.
                return 99

        # Return False if the engagement didn't start or has finished.
        return "Nope"

    def daysLeftToStartEngagement(self):
        todayDatetime = datetime.date.today()
        todayDate = datetime.date(
            todayDatetime.year, todayDatetime.month, todayDatetime.day)
        if (todayDate < self.StartDate):
            daysLeft = todayDate - self.StartDate
            # The -1 is to get positive numbers.
            return daysLeft * -1
        return"Nope"
    
    def workingEmp(self):
        return self.Employees.count()


class Comment(models.Model):
    eng = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name='comments')
    # Can't delete user that has comment
    user = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='user_id')
    body = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_on']

    def __str__(self):
        return 'Comment {} by {}'.format(self.body, self.user)

class Reports(models.Model):

    #Change filename to the name of the engagement
    def setFilename(instance,filename):
        path = "Reports/"
        name, extension = splitext(filename)
        return path + instance.eng.EngName + extension

    #Check file extension.    
    def validate_file_extension(value):
        if not value.name.endswith('.gpg'):
            raise ValidationError(u'Extension must be gpg')
            

    eng = models.ForeignKey(Engagement, on_delete=models.CASCADE)
    user = models.ForeignKey(Employee, on_delete=models.CASCADE)

    # To activate validation for uploaded files:
    # file = models.FileField(upload_to=setFilename, validators=[validate_file_extension])
    file = models.FileField(upload_to=setFilename)
    
    reference = models.CharField(max_length=36, default=uuid.uuid4)
    Types = (("Draft", "Draft"), ("Final", "Final"), ("Verification","Verification"))
    reportType = models.CharField(
        max_length=15, choices=Types, default="Draft", verbose_name="Report Type")
    note = models.CharField(max_length=60, null=True, blank=True)
    Timestamp = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        self.file.delete()
        super().delete(*args, **kwargs)  # Call the "real" save() method.