from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import models
from .models import (UserLoginLog, Course, Category, Chapter, Question, TestResult, UserProgress, TheoryProgress,
                     ChatMessage, Certificate)
import os
import matplotlib
import qrcode
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from calendar import monthrange
import base64
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, 'lmsapp', 'static', 'fonts', 'DejaVuSans.ttf')
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH))
    FONT_NAME = 'DejaVuSans'
else:
    FONT_NAME = 'Helvetica'

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
        is_admin = request.user.groups.first() and request.user.groups.first().name == 'Администратор'

        if is_admin:
            courses = Course.objects.filter(delete_date__isnull=True)
            total_courses_count = courses.count()
        else:
            courses = Course.objects.filter(delete_date__isnull=True)
            total_courses_count = courses.count()

        completed_courses_count = 0
        last_course = None
        last_course_percent = 0

        for course in courses:
            progress = UserProgress.objects.filter(user=request.user, course=course).first()
            if progress and progress.is_completed:
                completed_courses_count += 1
            if progress and progress.percent_complete > 0 and progress.percent_complete < 100:
                if last_course is None or progress.last_accessed > UserProgress.objects.filter(user=request.user,
                                                                                               course=last_course).first().last_accessed:
                    last_course = course
                    last_course_percent = progress.percent_complete

        if last_course is None:
            for course in courses:
                progress = UserProgress.objects.filter(user=request.user, course=course).first()
                if progress:
                    if last_course is None or progress.last_accessed > UserProgress.objects.filter(user=request.user,
                                                                                                   course=last_course).first().last_accessed:
                        last_course = course
                        last_course_percent = progress.percent_complete
                else:
                    if last_course is None:
                        last_course = course
                        last_course_percent = 0

        context = {
            'courses': courses,
            'total_courses_count': total_courses_count,
            'completed_courses_count': completed_courses_count,
            'last_course': last_course,
            'last_course_percent': last_course_percent,
        }
        return render(request, 'home.html', context)
    except Exception:
        messages.error(request, 'Ошибка', 'Не удалось загрузить курсы')
        return render(request, 'home.html',
                      {'courses': [], 'total_courses_count': 0, 'completed_courses_count': 0, 'last_course': None,
                       'last_course_percent': 0})


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
        certificate = Certificate.objects.filter(
            user=request.user,
            course=course,
            certificate_type='auto'
        ).first()

        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'total_chapters': chapters.count()}
        )

        if progress.total_chapters != chapters.count():
            progress.total_chapters = chapters.count()
            progress.save()
            update_user_progress_for_course(request.user, course)

        completed_tests = TestResult.objects.filter(
            user=request.user,
            chapter__course=course
        ).values_list('chapter_id', flat=True)

        completed_theory = TheoryProgress.objects.filter(
            user=request.user,
            chapter__course=course
        ).values_list('chapter_id', flat=True)

        completed_chapters = list(completed_tests) + list(completed_theory)

        context = {
            'course': course,
            'chapters': chapters,
            'completed_chapters': completed_chapters,
            'progress': progress,
            'certificate': certificate
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
        theory_completed = False

        if chapter.chapter_type == 'test':
            existing_result = TestResult.objects.filter(
                user=request.user,
                chapter=chapter
            ).first()
        else:
            theory_completed = TheoryProgress.objects.filter(
                user=request.user,
                chapter=chapter
            ).exists()

        context = {
            'chapter': chapter,
            'existing_result': existing_result,
            'theory_completed': theory_completed,
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

        update_user_progress_for_course(request.user, course)

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


@login_required
def mark_theory_complete(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, chapter_type='theory')

    existing, created = TheoryProgress.objects.get_or_create(
        user=request.user,
        chapter=chapter
    )

    if created:
        course = chapter.course
        update_user_progress_for_course(request.user, course)
        messages.success(request, 'Успешно', f'Глава "{chapter.title}" отмечена как прочитанная')
    else:
        messages.info(request, 'Информация', f'Вы уже отмечали эту главу как прочитанную')

    return redirect('chapter', chapter_id=chapter_id)


@login_required
def chapter_add_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    user_group = request.user.groups.first()
    if user_group and user_group.name == 'Гость':
        messages.error(request, 'Ошибка', 'У вас нет прав для добавления глав')
        return redirect('course_detail', course_id=course_id)

    return render(request, 'chapter_add.html', {'course': course})


@login_required
def chapter_edit_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    course = chapter.course
    questions = chapter.questions.all()

    user_group = request.user.groups.first()
    if user_group and user_group.name == 'Гость':
        messages.error(request, 'Ошибка', 'У вас нет прав для редактирования глав')
        return redirect('course_detail', course_id=course.id)

    return render(request, 'chapter_add.html', {
        'course': course,
        'chapter': chapter,
        'questions': questions
    })


@login_required
def save_chapter(request):
    if request.method != 'POST':
        return redirect('course')

    course_id = request.POST.get('course_id')
    chapter_id = request.POST.get('chapter_id')
    title = request.POST.get('title')
    chapter_type = request.POST.get('chapter_type')
    order = request.POST.get('order', 0)
    content = request.POST.get('content', '')

    if not title:
        messages.warning(request, 'Внимание', 'Название главы обязательно для заполнения')
        return redirect('chapter_add', course_id=course_id)

    try:
        order = int(order)
        if order < 1:
            order = 1
    except ValueError:
        order = 1

    course = get_object_or_404(Course, id=course_id)

    if chapter_id:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        old_order = chapter.order

        if old_order != order:
            if order > old_order:
                Chapter.objects.filter(course=course, order__gt=old_order, order__lte=order).update(
                    order=models.F('order') - 1)
            else:
                Chapter.objects.filter(course=course, order__gte=order, order__lt=old_order).update(
                    order=models.F('order') + 1)

        chapter.title = title
        chapter.chapter_type = chapter_type
        chapter.order = order
        chapter.content = content
        chapter.save()

        if chapter_type == 'test':
            chapter.questions.all().delete()
            question_texts = request.POST.getlist('question_texts[]')
            option_a_list = request.POST.getlist('option_a[]')
            option_b_list = request.POST.getlist('option_b[]')
            option_c_list = request.POST.getlist('option_c[]')
            option_d_list = request.POST.getlist('option_d[]')
            correct_answer_list = request.POST.getlist('correct_answer[]')

            for i in range(len(question_texts)):
                if question_texts[i] and option_a_list[i] and option_b_list[i]:
                    Question.objects.create(
                        chapter=chapter,
                        text=question_texts[i],
                        option_a=option_a_list[i],
                        option_b=option_b_list[i],
                        option_c=option_c_list[i] if i < len(option_c_list) else '',
                        option_d=option_d_list[i] if i < len(option_d_list) else '',
                        correct_answer=correct_answer_list[i] if i < len(correct_answer_list) else 'a'
                    )
    else:
        max_order = Chapter.objects.filter(course=course).aggregate(max_order=models.Max('order'))['max_order']
        if order > (max_order or 0) + 1:
            order = (max_order or 0) + 1

        Chapter.objects.filter(course=course, order__gte=order).update(order=models.F('order') + 1)

        chapter = Chapter.objects.create(
            course=course,
            title=title,
            chapter_type=chapter_type,
            order=order,
            content=content
        )

        if chapter_type == 'test':
            question_texts = request.POST.getlist('question_texts[]')
            option_a_list = request.POST.getlist('option_a[]')
            option_b_list = request.POST.getlist('option_b[]')
            option_c_list = request.POST.getlist('option_c[]')
            option_d_list = request.POST.getlist('option_d[]')
            correct_answer_list = request.POST.getlist('correct_answer[]')

            for i in range(len(question_texts)):
                if question_texts[i] and option_a_list[i] and option_b_list[i]:
                    Question.objects.create(
                        chapter=chapter,
                        text=question_texts[i],
                        option_a=option_a_list[i],
                        option_b=option_b_list[i],
                        option_c=option_c_list[i] if i < len(option_c_list) else '',
                        option_d=option_d_list[i] if i < len(option_d_list) else '',
                        correct_answer=correct_answer_list[i] if i < len(correct_answer_list) else 'a'
                    )

    update_user_progress_for_course(request.user, course)

    messages.success(request, 'Успешно', f'Глава "{title}" успешно сохранена')
    return redirect('course_detail', course_id=course_id)


def update_user_progress_for_course(user, course):
    completed_tests = TestResult.objects.filter(
        user=user,
        chapter__course=course
    ).count()

    completed_theory = TheoryProgress.objects.filter(
        user=user,
        chapter__course=course
    ).count()

    total_chapters = course.chapters.count()
    completed_chapters = completed_tests + completed_theory

    progress, _ = UserProgress.objects.get_or_create(
        user=user,
        course=course,
        defaults={'total_chapters': total_chapters}
    )

    progress.total_chapters = total_chapters
    progress.completed_chapters = completed_chapters
    progress.percent_complete = (completed_chapters / total_chapters) * 100 if total_chapters > 0 else 0

    if progress.percent_complete >= 100 and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
    elif progress.percent_complete < 100 and progress.is_completed:
        progress.is_completed = False
        progress.completed_at = None

    progress.save()


@login_required
def chapter_delete_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    course_id = chapter.course.id
    course = chapter.course

    user_group = request.user.groups.first()
    if user_group and user_group.name == 'Гость':
        messages.error(request, 'Ошибка', 'У вас нет прав для удаления глав')
        return redirect('course_detail', course_id=course_id)

    chapter_title = chapter.title
    deleted_order = chapter.order

    chapter.delete()

    Chapter.objects.filter(course=course, order__gt=deleted_order).update(order=models.F('order') - 1)

    update_user_progress_for_course(request.user, course)

    messages.success(request, 'Успешно', f'Глава "{chapter_title}" удалена')
    return redirect('course_detail', course_id=course_id)

def update_user_progress_for_course(user, course):
    completed_tests = TestResult.objects.filter(
        user=user,
        chapter__course=course
    ).count()

    completed_theory = TheoryProgress.objects.filter(
        user=user,
        chapter__course=course
    ).count()

    total_chapters = course.chapters.count()
    completed_chapters = completed_tests + completed_theory

    progress, created = UserProgress.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            'total_chapters': total_chapters,
            'completed_chapters': completed_chapters,
            'percent_complete': (completed_chapters / total_chapters) * 100 if total_chapters > 0 else 0
        }
    )

    if not created:
        progress.total_chapters = total_chapters
        progress.completed_chapters = completed_chapters
        progress.percent_complete = (completed_chapters / total_chapters) * 100 if total_chapters > 0 else 0

    if progress.percent_complete >= 100 and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
    elif progress.percent_complete < 100 and progress.is_completed:
        progress.is_completed = False
        progress.completed_at = None

    progress.save()

@login_required
def chat_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    chat_history = ChatMessage.objects.filter(course=course).order_by('id')
    return render(request, 'chat.html', {
        'course': course,
        'chat_history': chat_history
    })


@login_required
def certificate_list(request):
    user_group = request.user.groups.first()

    if user_group and user_group.name == 'Администратор':
        certificates = Certificate.objects.all()
    else:
        certificates = Certificate.objects.filter(user=request.user)

    expired_count = 0
    expires_soon = 0

    for cert in certificates:
        if cert.is_expired:
            expired_count += 1
        elif cert.days_until_expiry <= 30:
            expires_soon += 1

    return render(request, 'certificate_list.html', {
        'certificates': certificates,
        'expired_count': expired_count,
        'expires_soon': expires_soon,
        'is_admin': user_group and user_group.name == 'Администратор'
    })


@login_required
def certificate_add(request):
    if request.method == 'POST':
        try:
            certificate = Certificate(
                user_id=request.POST.get('user'),
                course_id=request.POST.get('course') or None,
                title=request.POST.get('title'),
                valid_from=request.POST.get('valid_from'),
                valid_until=request.POST.get('valid_until'),
                file=request.FILES.get('file'),
                notes=request.POST.get('notes')
            )
            certificate.save()
            messages.success(request, 'Успешно', 'Сертификат добавлен')
            return redirect('certificate_list')
        except Exception as e:
            messages.error(request, 'Ошибка', f'Не удалось добавить сертификат: {e}')

    users = User.objects.filter(is_active=True)
    courses = Course.objects.filter(delete_date__isnull=True)
    return render(request, 'certificate_form.html', {'users': users, 'courses': courses})

@login_required
def verify_certificate(request, cert_number):
    cert = get_object_or_404(Certificate, certificate_number=cert_number)
    return render(request, 'verify.html', {'cert': cert})

@login_required
def certificate_edit(request, cert_id):
    certificate = get_object_or_404(Certificate, id=cert_id)

    user_group = request.user.groups.first()
    if user_group and user_group.name != 'Администратор' and certificate.user != request.user:
        messages.error(request, 'Ошибка', 'Нет прав для редактирования')
        return redirect('certificate_list')

    if request.method == 'POST':
        certificate.title = request.POST.get('title')
        certificate.valid_from = request.POST.get('valid_from')
        certificate.valid_until = request.POST.get('valid_until')
        certificate.notes = request.POST.get('notes')
        if request.FILES.get('file'):
            certificate.file = request.FILES.get('file')
        certificate.save()
        messages.success(request, 'Успешно', 'Сертификат обновлён')
        return redirect('certificate_list')

    return render(request, 'certificate_form.html', {'certificate': certificate})


@login_required
def certificate_delete(request, cert_id):
    if request.user.groups.first().name != 'Администратор':
        messages.error(request, 'Ошибка', 'Нет прав для удаления')
        return redirect('certificate_list')

    certificate = get_object_or_404(Certificate, id=cert_id)
    certificate.delete()
    messages.success(request, 'Успешно', 'Сертификат удалён')
    return redirect('certificate_list')


@login_required
def download_certificate_pdf(request, cert_id):
    certificate = get_object_or_404(Certificate, id=cert_id)

    if certificate.user != request.user and request.user.groups.first().name != 'Администратор':
        messages.error(request, 'Ошибка', 'Нет доступа')
        return redirect('certificate_list')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    logo_path = os.path.join(BASE_DIR, 'lmsapp', 'static', 'images', 'kia-navlogo.png')
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            p.drawImage(logo, (width - 100) / 2, height - 90, width=100, height=50, preserveAspectRatio=True)
        except Exception as e:
            print(f"Ошибка логотипа: {e}")

    p.setStrokeColorRGB(0.6, 0.8, 0.2)
    p.setLineWidth(3)
    p.rect(30, 30, width - 60, height - 60)
    p.setLineWidth(1)
    p.rect(35, 35, width - 70, height - 70)

    p.setFont(FONT_NAME, 32)
    p.drawCentredString(width / 2, height - 160, "СЕРТИФИКАТ")
    p.setLineWidth(1.5)
    p.line(width / 2 - 120, height - 175, width / 2 + 120, height - 175)

    center_y = height / 2 + 50
    p.setFont(FONT_NAME, 14)
    p.drawCentredString(width / 2, center_y, "Настоящим подтверждается, что")
    p.setFont(FONT_NAME, 20)
    p.drawCentredString(width / 2, center_y - 40, certificate.user.get_full_name() or certificate.user.username)
    p.setFont(FONT_NAME, 14)
    p.drawCentredString(width / 2, center_y - 80, "успешно завершил(а)")
    p.setFont(FONT_NAME, 18)
    course_title = certificate.course.title if certificate.course else certificate.title
    p.drawCentredString(width / 2, center_y - 130, course_title)

    p.setFont(FONT_NAME, 12)
    p.drawCentredString(width / 2, 80, f"Дата выдачи: {certificate.issued_at.strftime('%d.%m.%Y')}")
    p.drawCentredString(width / 2, 60, f"Номер сертификата: {certificate.certificate_number}")

    qr_data = request.build_absolute_uri(f'/certificates/verify/{certificate.certificate_number}/')
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)

    # Настройки позиционирования
    qr_size = 60
    qr_x = width - 130  # Позиция QR-кода по горизонтали
    qr_y = 55  # Позиция QR-кода по вертикали

    # Рисуем QR-код
    p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    # Центрируем текст относительно QR-кода
    # Координата X для центра текста = X кода + (ширина кода / 2)
    text_center_x = qr_x + (qr_size / 2)

    p.setFont(FONT_NAME, 7)
    p.drawCentredString(text_center_x, qr_y - 10, "Проверить подлинность")

    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.id}.pdf"'
    return response