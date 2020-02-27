from .models import Engagement
import datetime


def alertUpcomingEngagements(request):
    todayDatetime = datetime.date.today()
    todayDate = datetime.date(
        todayDatetime.year, todayDatetime.month, todayDatetime.day)
    engs = Engagement.objects.filter(StartDate__gt=str(todayDate))
    alertEngagements = []
    endWithDays = {}
    for eng in engs:
        numDaysLeft = eng.daysLeftToStartEngagement()
        if (numDaysLeft.days <= 7):
            endWithDays['eng'] = eng

            endWithDays['days'] = numDaysLeft.days
            alertEngagements.append(endWithDays.copy())

    context = {
        'alertEngagements': alertEngagements
    }
    return context
