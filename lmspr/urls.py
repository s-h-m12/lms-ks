"""
URL configuration for lmspr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from lmsapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('course/', views.course_view, name='course'),
    path('course/<int:course_id>/', views.course_detail_view, name='course_detail'),
    path('chapter/<int:chapter_id>/', views.chapter_view, name='chapter'),
    path('submit-test/<int:chapter_id>/', views.submit_test, name='submit_test'),
    path('add/', views.add_view, name='add'),
    path('edit/<int:course_id>/', views.edit_view, name='edit'),
    path('save-course/', views.save_course, name='save_course'),
    path('soft-delete/<int:course_id>/', views.soft_delete_course, name='soft_delete'),
    path('hard-delete/<int:course_id>/', views.hard_delete_course, name='hard_delete'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('mark-theory-complete/<int:chapter_id>/', views.mark_theory_complete, name='mark_theory_complete'),
    path('chapter/add/<int:course_id>/', views.chapter_add_view, name='chapter_add'),
    path('chapter/edit/<int:chapter_id>/', views.chapter_edit_view, name='chapter_edit'),
    path('save-chapter/', views.save_chapter, name='save_chapter'),
    path('chapter/delete/<int:chapter_id>/', views.chapter_delete_view, name='chapter_delete'),
    path('chat/<int:course_id>/', views.chat_view, name='chat'),
    path('certificates/', views.certificate_list, name='certificate_list'),
    path('certificate/add/', views.certificate_add, name='certificate_add'),
    path('certificate/edit/<int:cert_id>/', views.certificate_edit, name='certificate_edit'),
    path('certificate/delete/<int:cert_id>/', views.certificate_delete, name='certificate_delete'),
    path('certificate/download/<int:cert_id>/', views.download_certificate_pdf, name='download_certificate_pdf'),
    path('certificate/verify/<str:cert_number>/', views.verify_certificate, name='verify_certificate'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/delete-avatar/', views.delete_avatar, name='delete_avatar'),
    path('my-learning/', views.my_learning_view, name='my_learning'),
    path('chat/', views.chat_list_view, name='chat_list'),
    path('chat/user/<int:user_id>/', views.chat_room_view, {'room_type': 'user'}, name='chat_user'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)