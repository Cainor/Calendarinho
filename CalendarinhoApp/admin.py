from django.contrib import admin
from django.core.exceptions import ValidationError
from threading import Thread

from .models import Employee, Engagement, Leave, Client, Service, Comment, ProjectManager, Report
from .employee import notifyManagersNewLeave
from .engagement import notifyEngagedEmployees, notifyManagersNewEngagement

from autocomplete.forms import EngagementForm, LeaveForm
admin.site.register(Employee)
admin.site.enable_nav_sidebar = True


class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'acronym', 'code')
    search_fields = ('name', 'acronym')


admin.site.register(Client, ClientAdmin)


class EngagementAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'service_type', 'start_date', 'end_date')
    list_filter = ('service_type', 'start_date')
    search_fields = ('name', 'client__name', 'scope')
    form = EngagementForm


    def save_model(self, request, obj, form, change):
        """Save engagement and send notifications to the related employees and managers."""
        # The variable obj.EngName is responsible for the engagement name, here you can automate it.

        # M = '{:02d}'.format(obj.StartDate.month)
        # Y = obj.StartDate.strftime("%y")
        # ClientObj = obj.CliName
        # clientCode = ClientObj.CliCode.strip()
        # obj.EngName = ""+str(M)+str(Y)+"-"+clientCode+"-"+ClientObj.CliShort+"-"+obj.ServiceType.serviceShort

        # Get employees before saving    
        empsBefore = list(obj.employees.all().values_list('id', flat=True)) if change else []

        super().save_model(request, obj, form, change)
        
        # Get employees after saving
        empsAfter = request.POST.getlist('employees')
        
        thread = Thread(target=notifyEngagedEmployees, args= (empsBefore, empsAfter, obj, request))
        thread.start()

        if not change:
            # Send notifications to the managers after a new engagement is added.
            thread = Thread(target=notifyManagersNewEngagement, args= (request.user, obj, request))
            thread.start()
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(EngagementAdmin, self).get_form(request, obj, **kwargs)
        return form

admin.site.register(Engagement, EngagementAdmin)


class LeaveAdmin(admin.ModelAdmin):
    list_display = ('note', 'employee', 'leave_type', 'start_date', 'end_date')
    list_filter = ('leave_type', 'start_date', 'end_date')
    search_fields = ('note', 'employee__first_name', 'employee__last_name')
    form = LeaveForm

    def save_model(self, request, obj, form, change):
        """Save Leave and send notifications to the related employees and managers."""
        obj.employee = request.user
        super().save_model(request, obj, form, change)
        if not change:
            # Send notifications to the managers after a new leave is added.
            thread = Thread(target = notifyManagersNewLeave, args= (request.user, obj, request))
            thread.start()            


admin.site.register(Leave, LeaveAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    search_fields = ('name', 'short_name')
admin.site.register(Service, ServiceAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body', 'engagement', 'created_on')
    list_filter = ['created_on']
    readonly_fields = ('user','body','engagement',)
    search_fields = ('user__username', 'body')


admin.site.register(Comment, CommentAdmin)
admin.site.register(ProjectManager)
