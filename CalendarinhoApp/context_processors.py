from .models import Employee, Engagement, Client
import datetime
from .forms import LeaveForm, EngagementForm, ClientForm
from django.conf import settings

def alertUpcomingEngagements(request):
    todayDatetime = datetime.date.today()
    todayDate = datetime.date(
        todayDatetime.year, todayDatetime.month, todayDatetime.day)
    engs = Engagement.objects.filter(start_date__gt=str(todayDate))
    alertEngagements = []
    endWithDays = {}
    for eng in engs:
        numDaysLeft = eng.days_left_to_start()
        #Alert engaged users before starting
        if (numDaysLeft <= settings.ALERT_ENG_DAYS and eng.employees.filter(id=request.user.id)):
            endWithDays['eng'] = eng
            endWithDays['days'] = numDaysLeft
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