from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('github/callback/', views.github_callback, name='github_callback'),
    path('sync/', views.sync_github, name='sync_github'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
