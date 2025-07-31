from django.shortcuts import render, redirect
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
        engs = Engagement.objects.filter(client_id=cli_id)
        
        # calculation fot the engagements card (bars)
        engsTable = []
        singleEng = {}
        for eng in engs:
            precent = eng.daysLeftPrecentage()
            if(precent != "Nope"):
                singleEng['engid'] = eng.id
                singleEng['engName'] = eng.name
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
        row["name"] = cli.name
        row["acronym"] = cli.acronym
        row["code"] = cli.code
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
            client = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"status": True, "id": client.id, "name": client.name})
            return redirect('CalendarinhoApp:client', cli_id=client.id)
    else:
        form = ClientForm()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"status": False}, status=400)
    
    return render(request, 'CalendarinhoApp/Create_Client.html', {'form': form})

from .views import not_found