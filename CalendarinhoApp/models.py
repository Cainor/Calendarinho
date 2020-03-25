from django.db import models
import datetime
from collections import namedtuple


class Employee(models.Model):
    EmpName = models.CharField(max_length=200)

    def __str__(self):
        return self.EmpName

    def getAllLeaves(self):
        event_arr = []
        all_leaves = Leave.objects.filter(emp_id=self.id)
        colors = ["#2C3E50", "#2980B9"]
        for i in all_leaves:
            event_sub_arr = {}
            event_sub_arr['empName'] = self.EmpName
            event_sub_arr['title'] = i.Note + " -- " + i.LeaveType
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['start'] = start_date
            event_sub_arr['end'] = end_date
            event_sub_arr['id'] = i.id
            event_sub_arr['color'] = colors[0] if i.LeaveType == "Vacation" else colors[1]
            event_arr.append(event_sub_arr)
        return event_arr

    def getAllEngagements(self):
        event_arr = []
        all_engagements = self.Engagements.all()
        colors = ["#BD4932"]
        for i in all_engagements:
            event_sub_arr = {}
            event_sub_arr['name'] = i.EngName
            start_date = datetime.datetime.strptime(
                str(i.StartDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.datetime.strptime(
                str(i.EndDate), "%Y-%m-%d").strftime("%Y-%m-%d")
            event_sub_arr['startDate'] = start_date
            event_sub_arr['endDate'] = end_date
            event_sub_arr['engID'] = i.id
            event_sub_arr['color'] = colors[0]
            event_sub_arr['serviceType'] = str(i.ServiceType)
            event_sub_arr['clientName'] = i.CliName
            event_arr.append(event_sub_arr)
        return event_arr

    # This method check if employee is availabile at a range of date
    def overlapCheck(self, StartDate, EndDate):
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


class Client(models.Model):
    CliName = models.CharField(max_length=200, verbose_name="Client Name")
    CliShort = models.CharField(max_length=10, verbose_name="Acronym")
    CliCode = models.CharField(max_length=4, default='9999')

    class Meta:
        ordering = ['CliName']

    def __str__(self):
        return str(self.CliName)


class Service(models.Model):
    serviceName = models.CharField(max_length=200, verbose_name="Service Name")
    serviceShort = models.CharField(
        max_length=10, verbose_name="Service Shortname")

    def __str__(self):
        return str(self.serviceName)


class Engagement(models.Model):
    EngName = models.CharField(max_length=200, verbose_name="Engagement Name")
    CliName = models.ForeignKey(
        Client, on_delete=models.PROTECT, verbose_name="Client Name")
    Employees = models.ManyToManyField(
        Employee, blank=True, related_name="Engagements")
    ServiceType = models.ForeignKey(
        Service, on_delete=models.PROTECT, verbose_name="Service Type")
    StartDate = models.DateField('Start Date')
    EndDate = models.DateField('End Date')

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


class Comment(models.Model):
    eng = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name='comments')
    # Can't delete user that has comment
    user = models.ForeignKey(
        Employee, to_field="username", on_delete=models.PROTECT)
    body = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_on']

    def __str__(self):
        return 'Comment {} by {}'.format(self.body, self.user)
