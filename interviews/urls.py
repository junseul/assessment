from django.urls import path

from . import views

app_name = 'interviews'

urlpatterns = [
    path('interview/', views.interview_detail, name='interview_detail'),
    path('interview/submit/', views.submit_response, name='submit_response'),
    path('interview/<int:pk>/follow-up/submit/', views.submit_follow_up, name='submit_follow_up'),
    path('interview/video/<int:pk>/', views.serve_video, name='serve_video'),
    path('interview/follow-up-video/<int:pk>/', views.serve_follow_up_video, name='serve_follow_up_video'),
]
