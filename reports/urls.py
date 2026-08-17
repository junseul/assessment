from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('reports/', views.candidate_list, name='candidate_list'),
    path('reports/<int:pk>/', views.candidate_detail, name='candidate_detail'),
]
