from .models import Engagement
import datetime
from .forms import LeaveForm, EngagementForm, ClientForm
from django.conf import settings

def alertUpcomingEngagements(request):
    todayDatetime = datetime.date.today()
    todayDate = datetime.date(
        todayDatetime.year, todayDatetime.month, todayDatetime.day)
    engs = Engagement.objects.filter(StartDate__gt=str(todayDate))
    alertEngagements = []
    endWithDays = {}
    for eng in engs:
        numDaysLeft = eng.daysLeftToStartEngagement()
        #Alert engaged users befor starting 
        if (numDaysLeft.days <= settings.ALERT_ENG_DAYS and eng.Employees.filter(id=request.user.id)):
            endWithDays['eng'] = eng

            endWithDays['days'] = numDaysLeft.days
            alertEngagements.append(endWithDays.copy())

    context = {
        'alertEngagements': alertEngagements
    }
    return context

def leave_form(request):
    return {
        'leave_form' : LeaveForm()
    }

def engagement_form(request):
    return {
        'engagement_form' : EngagementForm()
    }

def client_form(request):
    return {
        'client_form' : ClientForm()
    }