from django.urls import path

from . import views

app_name = 'traits'

urlpatterns = [
    path('survey/<int:pk>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:pk>/submit/', views.submit_response, name='submit_response'),
]
