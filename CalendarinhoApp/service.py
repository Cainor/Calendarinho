from django.shortcuts import render, redirect
from .models import Service
from .forms import ServiceForm
from django.contrib.auth.decorators import login_required
import logging
from django.http import JsonResponse

# Get an instance of a logger
logger = logging.getLogger(__name__)

@login_required
def ServiceCreate(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"status": True, "id": service.id, "name": service.name})
            return redirect('CalendarinhoApp:service', service_id=service.id)
    else:
        form = ServiceForm()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"status": False}, status=400)
    
    return render(request, 'CalendarinhoApp/Create_Service.html', {'form': form}) 