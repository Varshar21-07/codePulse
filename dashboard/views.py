from django.shortcuts import render, redirect
from django.db.models import Sum
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from .models import Stats, User
from .github_utils import (
    get_github_auth_url, get_access_token, fetch_github_user, 
    fetch_github_stats, calculate_productivity_score, fetch_github_repos
)
from datetime import datetime

def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    auth_url = get_github_auth_url(request)
    return render(request, 'dashboard/login.html', {'auth_url': auth_url})

def github_callback(request):
    code = request.GET.get('code')
    if not code:
        return redirect('dashboard:login')
    
    access_token = get_access_token(code)
    if not access_token:
        # Handle error
        return redirect('dashboard:login')
    
    user_data = fetch_github_user(access_token)
    github_username = user_data.get('login')
    email = user_data.get('email') or ""
    
    # Create or update user
    user, created = User.objects.get_or_create(username=github_username)
    if created:
        user.email = email
        user.set_unusable_password()
    
    user.github_username = github_username
    user.access_token = access_token
    user.save()
    
    login(request, user)
    
    # Initial sync
    sync_github_data(user)
    
    return redirect('dashboard:dashboard')

@login_required
def dashboard(request):
    detailed_prs = []
    user_stats = Stats.objects.filter(user=request.user, repo_name__isnull=True).first()
    
    if request.user.access_token:
        # Fetch fresh data including detailed PRs for the activity list
        raw_global = fetch_github_stats(request.user.access_token, request.user.github_username)
        save_stats(request.user, raw_global, None)
        user_stats = Stats.objects.filter(user=request.user, repo_name__isnull=True).first()
        detailed_prs = raw_global.get('detailed_prs', [])
    
    repos_count = 0
    if request.user.access_token:
        repos_data = fetch_github_repos(request.user.access_token)
        repos_count = len(repos_data)
    
    insights = []
    if user_stats:
        if user_stats.merged_prs > 5:
            insights.append("You're a PR machine! Keep merging.")
        else:
            insights.append("Start merging more PRs to boost your productivity score.")
            
        if user_stats.total_issues and user_stats.resolved_issues > user_stats.total_issues * 0.5:
            insights.append("Great job on resolving issues!")
        
    context = {
        'stats': user_stats,
        'insights': insights,
        'repos_count': repos_count,
        'detailed_prs': detailed_prs,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def sync_github(request):
    sync_github_data(request.user)
    return redirect('dashboard:dashboard')

def sync_github_data(user, repo_name=None):
    if not user.access_token:
        return
    
    # 1. Sync Global Stats
    raw_global = fetch_github_stats(user.access_token, user.github_username)
    save_stats(user, raw_global, None)
    
    # For now, we focus on global stats as per simplification request

def save_stats(user, raw_data, repo_name):
    prod_score = calculate_productivity_score(raw_data)
    
    # Mocking a streak for the interview demo
    mock_streak = 7 if raw_data.get('merged_prs', 0) > 0 else 0

    from django.utils import timezone
    Stats.objects.update_or_create(
        user=user,
        repo_name=repo_name,
        defaults={
            'total_prs': raw_data.get('total_prs', 0),
            'merged_prs': raw_data.get('merged_prs', 0),
            'open_prs': raw_data.get('open_prs', 0),
            'closed_prs': raw_data.get('closed_prs', 0),
            'total_issues': raw_data.get('total_issues', 0),
            'resolved_issues': raw_data.get('resolved_issues', 0),
            'productivity_score': prod_score,
            'streak_days': mock_streak,
            'last_synced': timezone.now(), # Force update
        }
    )
    print(f"Sync complete for {user.username} at {timezone.now()}")

@user_passes_test(is_admin)
def admin_dashboard(request):
    # Fetch all users with their global stats (repo_name=None)
    users = User.objects.all().prefetch_related('stats')
    
    # Calculate global metrics across all contributors
    all_global_stats = Stats.objects.filter(repo_name__isnull=True)
    
    global_metrics = {
        'total_users': users.count(),
        'total_prs': all_global_stats.aggregate(Sum('total_prs'))['total_prs__sum'] or 0,
        'total_merged': all_global_stats.aggregate(Sum('merged_prs'))['merged_prs__sum'] or 0,
        'total_issues': all_global_stats.aggregate(Sum('total_issues'))['total_issues__sum'] or 0,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', {
        'users': users, 
        'global_stats': global_metrics,
        'top_users': all_global_stats.order_by('-merged_prs')[:10]
    })

def leaderboard(request):
    top_users = Stats.objects.filter(repo_name__isnull=True).order_by('-merged_prs')[:10]
    return render(request, 'dashboard/leaderboard.html', {'top_users': top_users})

def logout_view(request):
    logout(request)
    return redirect('dashboard:login')
