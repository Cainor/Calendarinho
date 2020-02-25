from django.contrib import admin

from .models import Employee, Engagement, Leave, Client

admin.site.register(Employee)
admin.site.register(Client)
admin.site.register(Engagement)
admin.site.register(Leave)