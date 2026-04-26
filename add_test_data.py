import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lmspr.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from lmsapp.models import Category, Course, Chapter, Question, UserProgress

def add_test_data():
    print("Добавление тестовых данных...")

    category, _ = Category.objects.get_or_create(
        name='Программирование',
        defaults={'description': 'Курсы по программированию'}
    )

    course, _ = Course.objects.get_or_create(
        title='Тестовый курс по Django',
        defaults={
            'description': 'Курс для проверки работы тестов и прогресса',
            'category': category,
            'level': 'beginner',
            'duration_hours': 10,
            'status': 'published'
        }
    )

    chapter1, _ = Chapter.objects.get_or_create(
        course=course,
        title='Введение в Django',
        defaults={
            'chapter_type': 'theory',
            'order': 1,
            'content': 'Django - это высокоуровневый веб-фреймворк на Python. Он позволяет быстро создавать веб-приложения.'
        }
    )

    chapter2, _ = Chapter.objects.get_or_create(
        course=course,
        title='Тест: Основы Django',
        defaults={
            'chapter_type': 'test',
            'order': 2,
            'content': ''
        }
    )

    Question.objects.filter(chapter=chapter2).delete()
    questions_data = [
        {
            'text': 'Что означает аббревиатура MTV в Django?',
            'option_a': 'Model-View-Controller',
            'option_b': 'Model-Template-View',
            'option_c': 'Model-View-Template',
            'option_d': 'Module-Template-View',
            'correct': 'b'
        },
        {
            'text': 'Какой файл содержит настройки проекта Django?',
            'option_a': 'urls.py',
            'option_b': 'views.py',
            'option_c': 'models.py',
            'option_d': 'settings.py',
            'correct': 'd'
        },
        {
            'text': 'Какая команда создаёт новое приложение в Django?',
            'option_a': 'django startapp',
            'option_b': 'python manage.py startapp',
            'option_c': 'python startapp',
            'option_d': 'django-admin startproject',
            'correct': 'b'
        }
    ]

    for q in questions_data:
        Question.objects.create(
            chapter=chapter2,
            text=q['text'],
            option_a=q['option_a'],
            option_b=q['option_b'],
            option_c=q.get('option_c', ''),
            option_d=q.get('option_d', ''),
            correct_answer=q['correct']
        )

    print(f"Добавлен курс: {course.title}")
    print(f"  - Глава 1 (теория): {chapter1.title}")
    print(f"  - Глава 2 (тест): {chapter2.title} (вопросов: {chapter2.questions.count()})")
    print("\nГотово! Теперь можно зайти в Django shell и создать пользователя для тестирования.")

