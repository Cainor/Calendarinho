from django.contrib import admin

from .models import Employee, Engagement, Leave, Client, Service, Comment

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


admin.site.register(Engagement, EngagementAdmin)


class LeaveAdmin(admin.ModelAdmin):
    list_display = ('Note', 'emp', 'LeaveType', 'StartDate', 'EndDate')
    list_filter = ('LeaveType', 'StartDate', 'EndDate')
    search_fields = ('Note', 'emp__first_name', 'emp__last_name')


admin.site.register(Leave, LeaveAdmin)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('serviceName', 'serviceShort')
    search_fields = ('serviceName', 'serviceShort')


# if i added more serch fiels will generate error
admin.site.register(Service, ServiceAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body', 'eng', 'created_on')
    list_filter = ['created_on']
    readonly_fields = ('user',)
    search_fields = ('user__username', 'body')


admin.site.register(Comment, CommentAdmin)
