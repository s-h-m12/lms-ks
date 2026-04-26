from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import UserLoginLog, Course, Category, Chapter, Question, TestResult, UserProgress
import os
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from calendar import monthrange
import base64
from io import BytesIO


def login_view(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')

            if not username or not password:
                messages.error(request, 'Ошибка', 'Пожалуйста, заполните все поля')
                return render(request, 'login.html')

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                try:
                    UserLoginLog.objects.create(user=user)
                except Exception:
                    pass
                messages.success(request, 'Успешно', f'Добро пожаловать, {username}')
                return redirect('home')
            else:
                messages.error(request, 'Ошибка', 'Неверный логин или пароль')
                return render(request, 'login.html')
        except Exception:
            messages.error(request, 'Ошибка', 'Произошла ошибка. Попробуйте позже')
            return render(request, 'login.html')
    return render(request, 'login.html')


@login_required
def home_view(request):
    try:
        courses = Course.objects.filter(delete_date__isnull=True)
        return render(request, 'home.html', {'courses': courses})
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось загрузить курсы')
        return render(request, 'home.html', {'courses': []})


@login_required
def logout_view(request):
    try:
        logout(request)
        messages.info(request, 'До свидания', 'Вы вышли из системы')
    except Exception:
        pass
    return redirect('login')


@login_required
def course_view(request):
    try:
        is_admin = request.user.groups.first() and request.user.groups.first().name == 'Администратор'

        if is_admin:
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(delete_date__isnull=True)

        return render(request, 'course.html', {'courses': courses})
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось загрузить курсы')
        return render(request, 'course.html', {'courses': []})


@login_required
def course_detail_view(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id, delete_date__isnull=True)
        chapters = course.chapters.all()

        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'total_chapters': chapters.count()}
        )

        if progress.total_chapters != chapters.count():
            progress.total_chapters = chapters.count()
            progress.save()

        completed_chapters = TestResult.objects.filter(
            user=request.user,
            chapter__course=course
        ).values_list('chapter_id', flat=True)

        context = {
            'course': course,
            'chapters': chapters,
            'completed_chapters': list(completed_chapters),
            'progress': progress,
        }
        return render(request, 'course_detail.html', context)
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось загрузить содержимое курса')
        return redirect('course')


@login_required
def chapter_view(request, chapter_id):
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        existing_result = None
        if chapter.chapter_type == 'test':
            existing_result = TestResult.objects.filter(
                user=request.user,
                chapter=chapter
            ).first()

        context = {
            'chapter': chapter,
            'existing_result': existing_result,
        }
        return render(request, 'chapter_detail.html', context)
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось загрузить главу')
        return redirect('course')


@login_required
def submit_test(request, chapter_id):
    if request.method != 'POST':
        return redirect('chapter', chapter_id=chapter_id)

    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        questions = chapter.questions.all()

        if not questions:
            messages.warning(request, 'Внимание', 'В этом тесте пока нет вопросов')
            return redirect('chapter', chapter_id=chapter_id)

        existing = TestResult.objects.filter(user=request.user, chapter=chapter).first()
        if existing:
            messages.warning(request, 'Внимание', 'Вы уже проходили этот тест')
            return redirect('chapter', chapter_id=chapter_id)

        correct_count = 0
        total = questions.count()

        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer and answer.lower() == question.correct_answer.lower():
                correct_count += 1

        percent = (correct_count / total) * 100
        passed = percent >= 70

        TestResult.objects.create(
            user=request.user,
            chapter=chapter,
            score=correct_count,
            total_questions=total,
            percent=percent,
            passed=passed
        )

        course = chapter.course
        completed_tests = TestResult.objects.filter(
            user=request.user,
            chapter__course=course
        ).count()

        progress, _ = UserProgress.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'total_chapters': course.chapters.count()}
        )
        progress.completed_chapters = completed_tests
        progress.percent_complete = (
                                                completed_tests / progress.total_chapters) * 100 if progress.total_chapters > 0 else 0

        if progress.percent_complete >= 100:
            progress.is_completed = True
            progress.completed_at = timezone.now()

        progress.save()

        if passed:
            messages.success(request, 'Поздравляем!',
                             f'Вы прошли тест! Результат: {correct_count}/{total} ({percent:.0f}%)')
        else:
            messages.warning(request, 'Тест не пройден',
                             f'Результат: {correct_count}/{total} ({percent:.0f}%). Нужно набрать 70%')

        return redirect('chapter', chapter_id=chapter_id)
    except Exception:
        messages.error(request, 'Ошибка', 'Произошла ошибка при проверке теста')
        return redirect('course')


@login_required
def statistics_view(request):
    try:
        period = request.GET.get('period', 'month')
        selected_date = request.GET.get('date', '')

        today = timezone.now().date()

        if not selected_date:
            if period == 'month':
                selected_date = today.strftime('%Y-%m')
            elif period == 'quarter':
                quarter = (today.month - 1) // 3 + 1
                selected_date = f"{today.year}-Q{quarter}"
            else:
                selected_date = str(today.year)

        if period == 'month':
            year, month = map(int, selected_date.split('-'))
            start_date = datetime(year, month, 1).date()
            last_day = monthrange(year, month)[1]

            logins_by_day = {}
            for day in range(1, last_day + 1):
                date = datetime(year, month, day).date()
                logins_by_day[date] = UserLoginLog.objects.filter(
                    login_time__date=date
                ).count()

            dates = list(logins_by_day.keys())
            counts = list(logins_by_day.values())

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(dates, counts, marker='o', color='#9ACC39', linewidth=2, markersize=4)
            ax.fill_between(dates, counts, color='#9ACC39', alpha=0.2)
            ax.set_title(f'Активность пользователей за {month:02d}.{year}', fontsize=12, pad=15)
            ax.set_xlabel('Дата', fontsize=10)
            ax.set_ylabel('Количество входов', fontsize=10)
            ax.grid(True, alpha=0.3, linestyle='--')
            plt.xticks(rotation=45, fontsize=8)
            plt.yticks(fontsize=8)

        elif period == 'quarter':
            year = int(selected_date[:4])
            quarter = int(selected_date[-1])
            quarters = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
            start_month, end_month = quarters[quarter]
            start_date = datetime(year, start_month, 1).date()
            if end_month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, end_month + 1, 1).date() - timedelta(days=1)

            logins_by_week = {}
            current = start_date
            week_num = 1
            while current <= end_date:
                week_end = current + timedelta(days=6)
                if week_end > end_date:
                    week_end = end_date
                count = UserLoginLog.objects.filter(
                    login_time__date__gte=current,
                    login_time__date__lte=week_end
                ).count()
                logins_by_week[f'Неделя {week_num}'] = count
                current = week_end + timedelta(days=1)
                week_num += 1

            labels = list(logins_by_week.keys())
            counts = list(logins_by_week.values())

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(labels, counts, color='#9ACC39', alpha=0.7)
            ax.set_title(f'Активность пользователей за {quarter}-й квартал {year} года', fontsize=12, pad=15)
            ax.set_xlabel('Период', fontsize=10)
            ax.set_ylabel('Количество входов', fontsize=10)
            plt.xticks(rotation=45, fontsize=8)
            plt.yticks(fontsize=8)

        else:
            year = int(selected_date)

            logins_by_month = {}
            for month in range(1, 13):
                month_start = datetime(year, month, 1).date()
                last_day = monthrange(year, month)[1]
                month_end = datetime(year, month, last_day).date()
                count = UserLoginLog.objects.filter(
                    login_time__date__gte=month_start,
                    login_time__date__lte=month_end
                ).count()
                logins_by_month[f'{month:02d}.{year}'] = count

            labels = list(logins_by_month.keys())
            counts = list(logins_by_month.values())

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(labels, counts, color='#9ACC39', alpha=0.7)
            ax.set_title(f'Активность пользователей за {year} год', fontsize=12, pad=15)
            ax.set_xlabel('Месяц', fontsize=10)
            ax.set_ylabel('Количество входов', fontsize=10)
            plt.xticks(rotation=45, fontsize=8)
            plt.yticks(fontsize=8)

        fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.15)

        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches=None, pad_inches=0)
        buffer.seek(0)
        chart_image = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        plt.close(fig)

        context = {
            'chart_image': chart_image,
            'period': period,
            'selected_date': selected_date,
        }

        return render(request, 'statistics.html', context)

    except Exception as e:
        messages.error(request, 'Ошибка', 'Не удалось загрузить статистику')
        return render(request, 'statistics.html', {'chart_image': None})


@login_required
def add_view(request):
    try:
        return render(request, 'crud.html')
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось открыть страницу')
        return redirect('course')


@login_required
def edit_view(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        return render(request, 'crud.html', {'course': course})
    except Course.DoesNotExist:
        messages.error(request, 'Ошибка', f'Курс с ID {course_id} не найден')
        return redirect('course')
    except Exception:
        messages.error(request, 'Ошибка', 'Произошла ошибка')
        return redirect('course')


@login_required
def save_course(request):
    if request.method != 'POST':
        return redirect('course')

    try:
        course_id = request.POST.get('course_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_name = request.POST.get('category')
        level = request.POST.get('level')
        duration_hours = request.POST.get('duration_hours')
        status = request.POST.get('status')
        image = request.FILES.get('image')

        if not title:
            messages.warning(request, 'Внимание', 'Название курса обязательно для заполнения')
            return redirect('course')

        if not description:
            messages.warning(request, 'Внимание', 'Описание курса обязательно для заполнения')
            return redirect('course')

        try:
            duration_hours = int(duration_hours) if duration_hours else 0
        except ValueError:
            duration_hours = 0

        category, _ = Category.objects.get_or_create(name=category_name)

        if course_id and course_id != '':
            try:
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
                messages.success(request, 'Успешно', f'Курс "{title}" успешно обновлён')
            except Exception:
                messages.error(request, 'Ошибка', 'Не удалось обновить курс')
        else:
            try:
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
                messages.success(request, 'Успешно', f'Курс "{title}" успешно создан')
            except Exception:
                messages.error(request, 'Ошибка', 'Не удалось создать курс')

        return redirect('course')

    except Exception:
        messages.error(request, 'Ошибка', 'Произошла непредвиденная ошибка')
        return redirect('course')


@login_required
def soft_delete_course(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        course.delete_date = timezone.now()
        course.save()
        messages.warning(request, 'Внимание', f'Курс "{course.title}" перемещён в корзину')
    except Course.DoesNotExist:
        messages.error(request, 'Ошибка', 'Курс не найден')
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось выполнить мягкое удаление')
    return HttpResponseRedirect(reverse('course'))


@login_required
def hard_delete_course(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
        course_title = course.title
        if course.image and os.path.isfile(course.image.path):
            os.remove(course.image.path)
        course.delete()
        messages.success(request, 'Успешно', f'Курс "{course_title}" полностью удалён из системы')
    except Course.DoesNotExist:
        messages.error(request, 'Ошибка', 'Курс не найден')
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось выполнить полное удаление')
    return HttpResponseRedirect(reverse('course'))