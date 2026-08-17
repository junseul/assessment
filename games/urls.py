from django.urls import path

from . import views

app_name = 'games'

urlpatterns = [
    path('games/go-nogo/', views.go_nogo, name='go_nogo'),
    path('games/go-nogo/submit/', views.submit_result, name='submit_result'),
]
