from django.urls import path

from . import views

app_name = 'games'

urlpatterns = [
    path('games/', views.index, name='index'),
    path('games/admin/grid/', views.admin_grid, name='admin_grid'),
    path('games/expedition-investment/round/', views.expedition_round, name='expedition_round'),
    path('games/<slug:slug>/', views.play, name='play'),
    path('games/<slug:slug>/submit/', views.submit_result, name='submit_result'),
]
