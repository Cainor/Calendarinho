# Generated by Django 2.2.6 on 2020-02-02 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CalendarinhoApp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='Engagements',
        ),
        migrations.AddField(
            model_name='engagement',
            name='Employees',
            field=models.ManyToManyField(blank=True, related_name='Engagements', to='CalendarinhoApp.Employee'),
        ),
    ]
