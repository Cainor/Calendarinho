from django.contrib import admin

from .models import Employee, Engagement, Leave, Client, Service, Comment

admin.site.register(Employee)
admin.site.register(Client)
admin.site.register(Engagement)
admin.site.register(Leave)
admin.site.register(Service)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'body', 'eng', 'created_on')
    list_filter = ['created_on']
    readonly_fields = ('user',)
    search_fields = ('user__username', 'body')


admin.site.register(Comment, CommentAdmin)
