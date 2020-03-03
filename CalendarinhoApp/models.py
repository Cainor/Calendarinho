from django.db import models
import datetime
from collections import namedtuple
from users.models import CustomUser as Employee


class Client(models.Model):
    CliName = models.CharField(max_length=200)
    CliShort = models.CharField(max_length=10)

    def __str__(self):
        return str(self.CliName)


class Engagement(models.Model):
    EngName = models.CharField(max_length=200)
    CliName = models.ForeignKey(Client, on_delete=models.PROTECT)
    Employees = models.ManyToManyField(
        Employee, blank=True, related_name="Engagements")
    services = (("Non", "--"), ("WVA", "Web Vulnerability Asseessment"), ("WPT", "Web Penetration Testing"), ("SCR",
                                                                                                              "Source Code Review"), ("NVA", "Network Vulnerability Asseessment"), ("NPT", "Network Penetration Testing"))
    ServiceType = models.CharField(
        max_length=3, choices=services, default="Non")
    StartDate = models.DateField('Start Date')
    EndDate = models.DateField('End Date')

    def getAllEngs():
        event_arr = []
        all_events = Engagement.objects.all()
        colors = ["#277D9C", "#09ADA9", "#461AAD",
                  "#9E0034", "#B7410E", "#446600"]
        for i in all_events:
            event_sub_arr = {}
            event_sub_arr['title'] = i.EngName + " -- " + i.ServiceType
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            event_sub_arr['color'] = colors[i.id % len(colors)]
            event_arr.append(event_sub_arr)
        return event_arr

    def __str__(self):
        return str(self.EngName + " - " + self.ServiceType)

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


class Leave(models.Model):
    emp = models.ForeignKey(Employee, on_delete=models.CASCADE)
    Note = models.CharField(max_length=200)
    StartDate = models.DateField('Start Date')
    EndDate = models.DateField('End Date')
    Types = (("Training", "Training"), ("Vacation", "Vacation"))
    LeaveType = models.CharField(
        max_length=8, choices=Types, default="Vacation")

    def __str__(self):
        return str(self.LeaveType) + " -- " + str(self.Note)
