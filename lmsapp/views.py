from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from .models import UserLoginLog, Course, Category
import os


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
            return render(request, 'login.html', {'error': 'Некорректные данные'})
    return render(request, 'login.html')


@login_required
def home_view(request):
    courses = Course.objects.filter(delete_date__isnull=True)
    return render(request, 'home.html', {'courses': courses})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def course_view(request):
    courses = Course.objects.filter(delete_date__isnull=True)
    return render(request, 'course.html', {'courses': courses})


@login_required
def add_view(request):
    return render(request, 'crud.html')


@login_required
def edit_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'crud.html', {'course': course})


@login_required
def save_course(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_name = request.POST.get('category')
        level = request.POST.get('level')
        duration_hours = request.POST.get('duration_hours')
        status = request.POST.get('status')
        image = request.FILES.get('image')

        print(f"DEBUG: course_id = {course_id}")  # Отладка
        print(f"DEBUG: title = {title}")

        category, _ = Category.objects.get_or_create(name=category_name)

        if course_id and course_id != '':
            # Редактирование
            course = get_object_or_404(Course, id=course_id)
            course.title = title
            course.description = description
            course.category = category
            course.level = level
            course.duration_hours = duration_hours
            course.status = status
            if image:
                course.image = image
            course.save()
            print(f"DEBUG: Курс {course_id} обновлён")
        else:
            # Создание нового
            course = Course(
                title=title,
                description=description,
                category=category,
                level=level,
                duration_hours=duration_hours,
                status=status,
                image=image
            )
            course.save()
            print(f"DEBUG: Новый курс создан")

        return redirect('course')

    return redirect('course')


@login_required
def soft_delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete_date = timezone.now()
    course.save()
    return HttpResponseRedirect(reverse('course'))


@login_required
def hard_delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    return HttpResponseRedirect(reverse('course'))