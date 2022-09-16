from django.shortcuts import render
from .models import Engagement, Client
from .forms import *
from django.contrib.auth.decorators import login_required
import logging
from django.http import JsonResponse
from django.conf import settings

# Get an instance of a logger
logger = logging.getLogger(__name__)


@login_required
def client(request, cli_id):
    try:
        cli = Client.objects.get(id=cli_id)
        engs = Engagement.objects.filter(CliName_id=cli_id)
        
        # calculation fot the engagements card (bars)
        engsTable = []
        singleEng = {}
        for eng in engs:
            precent = eng.daysLeftPrecentage()
            if(precent != "Nope"):
                singleEng['engid'] = eng.id
                singleEng['engName'] = eng.EngName
                singleEng['precent'] = precent
                engsTable.append(singleEng.copy())
        engsTable = sorted(engsTable, key=lambda i: i['precent'])

        context = {'cli': cli,
                   'engs': engs,
                   'engagementsBars':engsTable}
    except Client.DoesNotExist:
        return not_found(request)

    return render(request, "CalendarinhoApp/client.html", context)


@login_required
def ClientsTable(request):
    clients = Client.objects.all()
    table = []
    row = {}
    for cli in clients:
        row["cliID"] = cli.id
        row["name"] = cli.CliName
        row["acronym"] = cli.CliShort
        row["code"] = cli.CliCode
        table.append(row.copy())

    context = {
        'table': table
    }
    return render(request, "CalendarinhoApp/ClientsTable.html", context)

@login_required
def ClientCreate(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            result = {"status": True}
            return JsonResponse(result)
    
    result = {"status": False}
    return JsonResponse(result, status=500)

from .views import not_found