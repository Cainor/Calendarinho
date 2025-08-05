from .models import Employee, Engagement, Client
import datetime
from .forms import LeaveForm, EngagementForm, ClientForm, ServiceForm
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

def service_form(request):
    return {
        'service_form' : ServiceForm()
    }

def global_stats(request):
    """Provide global statistics to all templates using optimized service functions"""
    if not request.user.is_authenticated:
        return {}
    
    try:
        from .service import get_dashboard_summary
        
        # Use optimized dashboard summary function
        dashboard_data = get_dashboard_summary()
        
        return {
            'global_stats': {
                'employees': dashboard_data['employees'],
                'engagements': dashboard_data['engagements'],
                'clients': dashboard_data['clients'],
                'utilization_rate': dashboard_data['utilization']
            }
        }
    except Exception:
        # Return empty dict if there's any error to prevent template rendering issues
        return {}