from django.test import TestCase
from django.utils import timezone
from .models import Course, Category


class CourseModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Программирование')
        self.course = Course.objects.create(
            title='Тестовый курс',
            description='Описание тестового курса',
            category=self.category,
            level='beginner',
            duration_hours=10,
            status='published'
        )

    def test_course_creation(self):
        self.assertEqual(self.course.title, 'Тестовый курс')
        self.assertEqual(self.course.category.name, 'Программирование')

    def test_soft_delete(self):
        self.course.delete_date = timezone.now()
        self.course.save()
        active_courses = Course.objects.filter(delete_date__isnull=True)
        self.assertNotIn(self.course, active_courses)