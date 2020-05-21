from django.contrib import admin

from .models import Employee, Engagement, Leave, Client, Service, Comment
from .views import notifyEngagedEmployees, notifyManagersNewEngagement, notifyManagersNewLeave

admin.site.register(Employee)


class ClientAdmin(admin.ModelAdmin):
    list_display = ('CliName', 'CliShort', 'CliCode')
    search_fields = ('CliName', 'CliShort')


admin.site.register(Client, ClientAdmin)


class EngagementAdmin(admin.ModelAdmin):
    list_display = ('EngName', 'CliName', 'ServiceType',
                    'StartDate', 'EndDate')
    list_filter = ('ServiceType', 'StartDate')
    search_fields = ('EngName', 'CliName__CliName')


    def save_model(self, request, obj, form, change):
        """Save engagement and send notifications to the related employees and managers."""

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
    
        notifyEngagedEmployees(empsBefore, empsAfter, engagement=obj, request=request)

        if not change:
            # Send notifications to the managers after a new engagement is added.
            notifyManagersNewEngagement(user=request.user, engagement=obj ,request=request)

admin.site.register(Engagement, EngagementAdmin)


class LeaveAdmin(admin.ModelAdmin):
    list_display = ('Note', 'emp', 'LeaveType', 'StartDate', 'EndDate')
    list_filter = ('LeaveType', 'StartDate', 'EndDate')
    search_fields = ('Note', 'emp__first_name', 'emp__last_name')

    def save_model(self, request, obj, form, change):
        """Save Leave and send notifications to the related employees and managers."""

        super().save_model(request, obj, form, change)
        if not change:
            # Send notifications to the managers after a new leave is added.
            notifyManagersNewLeave(user=request.user, leave=obj, request=request)


admin.site.register(Leave, LeaveAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('serviceName', 'serviceShort')
    search_fields = ('serviceName', 'serviceShort')


admin.site.register(Service, ServiceAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body', 'eng', 'created_on')
    list_filter = ['created_on']
    readonly_fields = ('user',)
    search_fields = ('user__username', 'body')


admin.site.register(Comment, CommentAdmin)
