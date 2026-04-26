from django.db import models
import os
from PIL import Image
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название категории')
    description = models.TextField(blank=True, verbose_name='Описание')
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата удаления')


class Course(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
        ('archived', 'Архив'),
    ]

    LEVEL_CHOICES = [
        ('beginner', 'Начальный'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название курса')
    description = models.TextField(verbose_name='Описание')
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL, verbose_name='Категория')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_hours = models.PositiveIntegerField(default=0, verbose_name='Длительность (часы)')

    image = models.ImageField(
        upload_to='course_images/',
        verbose_name='Обложка курса',
        blank=True,
        null=True
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата удаления')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and os.path.isfile(self.image.path):
            img = Image.open(self.image.path)
            img = img.resize((300, 200), Image.Resampling.LANCZOS)
            img.save(self.image.path)


class Chapter(models.Model):
    CHAPTER_TYPE_CHOICES = [
        ('theory', 'Теоретический материал'),
        ('test', 'Тест'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters', verbose_name='Курс')
    title = models.CharField(max_length=200, verbose_name='Название главы')
    chapter_type = models.CharField(max_length=20, choices=CHAPTER_TYPE_CHOICES, default='theory',
                                    verbose_name='Тип главы')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядковый номер')
    content = models.TextField(blank=True, verbose_name='Теоретический материал')

    class Meta:
        ordering = ['order']


class Question(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='questions', verbose_name='Глава')
    text = models.TextField(verbose_name='Текст вопроса')
    option_a = models.CharField(max_length=500, verbose_name='Вариант А')
    option_b = models.CharField(max_length=500, verbose_name='Вариант Б')
    option_c = models.CharField(max_length=500, blank=True, verbose_name='Вариант В')
    option_d = models.CharField(max_length=500, blank=True, verbose_name='Вариант Г')
    correct_answer = models.CharField(
        max_length=1,
        choices=[('a', 'A'), ('b', 'Б'), ('c', 'В'), ('d', 'Г')],
        verbose_name='Правильный ответ'
    )


class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name='Пользователь')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='results', verbose_name='Глава')
    score = models.PositiveIntegerField(default=0, verbose_name='Количество правильных ответов')
    total_questions = models.PositiveIntegerField(default=0, verbose_name='Всего вопросов')
    percent = models.FloatField(default=0, verbose_name='Процент выполнения')
    passed = models.BooleanField(default=False, verbose_name='Тест пройден')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата прохождения')

    class Meta:
        unique_together = ['user', 'chapter']


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress', verbose_name='Пользователь')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress', verbose_name='Курс')
    completed_chapters = models.PositiveIntegerField(default=0, verbose_name='Пройдено глав')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='Всего глав')
    percent_complete = models.FloatField(default=0, verbose_name='Процент прохождения курса')
    is_completed = models.BooleanField(default=False, verbose_name='Курс завершён')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения курса')
    last_accessed = models.DateTimeField(auto_now=True, verbose_name='Последний доступ')

    class Meta:
        unique_together = ['user', 'course']


class UserLoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logins', verbose_name='Пользователь')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='Время входа')