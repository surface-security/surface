from django.shortcuts import render, get_object_or_404
from .models import Secret

def secret_list(request):
    secrets = Secret.objects.all()
    return render(request, 'secretsmanager/secret_list.html', {'secrets': secrets})

def secret_detail(request, pk):
    secret = get_object_or_404(Secret, pk=pk)
    return render(request, 'secretsmanager/secret_detail.html.html', {'secret': secret})