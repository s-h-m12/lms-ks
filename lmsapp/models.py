from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import os
from PIL import Image


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

    # Основные поля
    title = models.CharField(max_length=200, verbose_name='Название курса')
    description = models.TextField(verbose_name='Описание')
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL, verbose_name='Категория')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_hours = models.PositiveIntegerField(default=0, verbose_name='Длительность (часы)')

    # Изображение
    image = models.ImageField(
        upload_to='course_images/',
        verbose_name='Обложка курса',
        blank=True,
        null=True
    )

    # Статус и мягкое удаление
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата удаления')

    # Служебные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Изменение размера на 300x200
        if self.image and os.path.isfile(self.image.path):
            img = Image.open(self.image.path)
            img = img.resize((300, 200), Image.Resampling.LANCZOS)
            img.save(self.image.path)
