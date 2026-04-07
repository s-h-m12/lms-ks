from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import UserLoginLog
from django.utils import timezone
from django.contrib.auth.models import User

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            UserLoginLog.objects.create(user=user)
            return redirect('home')
        else:
            return render(request,'login.html',{'error': 'Некорректные данные'})
    return render(request, 'login.html')

def home_view(request):
    return render(request, 'home.html')
