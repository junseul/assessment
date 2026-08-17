from django.urls import path

from . import views

app_name = 'invites'

urlpatterns = [
    path('local-test/<slug:stage>/', views.local_test, name='local_test'),
    path('invite/<str:token>/', views.verify, name='verify'),
    path('start/', views.start, name='start'),
    path('no-access/', views.no_access, name='no_access'),
]
