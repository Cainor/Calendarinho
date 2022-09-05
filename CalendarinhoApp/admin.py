from django.contrib import admin
from django.core.exceptions import ValidationError
from threading import Thread

from .models import Employee, Engagement, Leave, Client, Service, Comment, ProjectManager
from .employee import notifyManagersNewLeave
from .engagement import notifyEngagedEmployees, notifyManagersNewEngagement

from autocomplete.forms import EngagementForm, LeaveForm
admin.site.register(Employee)
admin.site.enable_nav_sidebar = False


class ClientAdmin(admin.ModelAdmin):
    list_display = ('CliName', 'CliShort', 'CliCode')
    search_fields = ('CliName', 'CliShort')


admin.site.register(Client, ClientAdmin)


class EngagementAdmin(admin.ModelAdmin):
    list_display = ('EngName', 'CliName', 'ServiceType',
                    'StartDate', 'EndDate')
    list_filter = ('ServiceType', 'StartDate')
    search_fields = ('EngName', 'CliName__CliName', 'Scope')
    form = EngagementForm


    def save_model(self, request, obj, form, change):
        """Save engagement and send notifications to the related employees and managers."""
        # The variable obj.EngName is responsible for the engagement name, here you can automate it.

        # M = '{:02d}'.format(obj.StartDate.month)
        # Y = obj.StartDate.strftime("%y")
        # ClientObj = obj.CliName
        # clientCode = ClientObj.CliCode.strip()
        # obj.EngName = ""+str(M)+str(Y)+"-"+clientCode+"-"+ClientObj.CliShort+"-"+obj.ServiceType.serviceShort

        super().save_model(request, obj, form, change)

        # Send notifications to the related employees.
        empsBefore=None
        if change:
            empsBefore = obj.Employees.all()
            if empsBefore.count() < 1:
                empsBefore = None
        empsAfter=None
        if request.POST.getlist('Employees'):
            empsAfter=Employee.objects.filter(id__in=request.POST.getlist('Employees'))
        
        thread = Thread(target = notifyEngagedEmployees, args= (empsBefore, empsAfter, obj, request))
        thread.start()

        if not change:
            # Send notifications to the managers after a new engagement is added.
            thread = Thread(target = notifyManagersNewEngagement, args= (request.user, obj, request))
            thread.start()
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(EngagementAdmin, self).get_form(request, obj, **kwargs)
        return form

admin.site.register(Engagement, EngagementAdmin)


class LeaveAdmin(admin.ModelAdmin):
    list_display = ('Note', 'emp', 'LeaveType', 'StartDate', 'EndDate')
    list_filter = ('LeaveType', 'StartDate', 'EndDate')
    search_fields = ('Note', 'emp__first_name', 'emp__last_name')
    form = LeaveForm

    def save_model(self, request, obj, form, change):
        """Save Leave and send notifications to the related employees and managers."""
        obj.emp = request.user
        super().save_model(request, obj, form, change)
        if not change:
            # Send notifications to the managers after a new leave is added.
            thread = Thread(target = notifyManagersNewLeave, args= (request.user, obj, request))
            thread.start()            


admin.site.register(Leave, LeaveAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('serviceName', 'serviceShort')
    search_fields = ('serviceName', 'serviceShort')

admin.site.register(Service, ServiceAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body', 'eng', 'created_on')
    list_filter = ['created_on']
    readonly_fields = ('user','body','eng',)
    search_fields = ('user__username', 'body')


admin.site.register(Comment, CommentAdmin)
admin.site.register(ProjectManager)
