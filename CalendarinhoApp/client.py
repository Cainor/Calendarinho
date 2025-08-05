from django.shortcuts import render, redirect
from .models import Engagement, Client
from .forms import *
from django.contrib.auth.decorators import login_required
import logging
import datetime
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
            precent = eng.days_left_percentage()
            if(precent != "Nope"):
                singleEng['engid'] = eng.id
                singleEng['engName'] = eng.name
                singleEng['precent'] = precent
                engsTable.append(singleEng.copy())
        engsTable = sorted(engsTable, key=lambda i: i['precent'])

        # Get vulnerability summary for the client
        vulnerability_summary = cli.get_vulnerability_summary()

        context = {'cli': cli,
                   'engs': engs,
                   'engagementsBars': engsTable,
                   'vulnerability_summary': vulnerability_summary}
    except Client.DoesNotExist:
        return not_found(request)

    return render(request, "CalendarinhoApp/client.html", context)


@login_required
def ClientsTable(request):
    # Use optimized service function for better performance
    from .service import get_enhanced_client_data
    from .forms import AdvancedClientFilterForm
    
    # Initialize filter form
    filter_form = AdvancedClientFilterForm(request.GET or None)
    
    # Get enhanced client data with optimized queries
    data = get_enhanced_client_data()
    
    # If this is an AJAX request for filtered data, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from .api_filters import apply_client_filters, paginate_data
        
        filters = {}
        if filter_form.is_valid():
            filters = {k: v for k, v in filter_form.cleaned_data.items() if v is not None and v != ''}
        
        # Apply filters
        filtered_clients = apply_client_filters(data['clients'], filters)
        
        # Sort options
        sort_by = request.GET.get('sort_by', 'name')
        sort_order = request.GET.get('sort_order', 'asc')
        
        if sort_by in ['name', 'activity_level', 'risk_score', 'total_engagements']:
            reverse_sort = sort_order == 'desc'
            filtered_clients.sort(
                key=lambda x: x.get(sort_by, ''), 
                reverse=reverse_sort
            )
        
        # Pagination
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 25))
        
        paginated_data = paginate_data(filtered_clients, page, per_page)
        
        return JsonResponse({
            'success': True,
            'clients': paginated_data['data'],
            'pagination': paginated_data['pagination'],
            'summary': {
                'total_filtered': len(filtered_clients),
                'total_unfiltered': len(data['clients']),
                'client_stats': data['client_stats'],
                'filters_applied': len([k for k, v in filters.items() if v])
            }
        })
    
    context = {
        'table': data['clients'],
        'client_stats': data['client_stats'],
        'filter_form': filter_form,
        'total_clients': len(data['clients'])
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