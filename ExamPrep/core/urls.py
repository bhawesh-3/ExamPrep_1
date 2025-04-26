from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name="register"),
    path('login/', views.user_login, name='login'),  # Changed to use our custom login view
    path('logout/', views.custom_logout, name='logout'),
    path('syllabus_input/', views.syllabus_input, name="syllabus_input"),
    path('notes/', views.notes, name="notes"),
    path('quiz/', views.quiz, name="quiz"),
]
