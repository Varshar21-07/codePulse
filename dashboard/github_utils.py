import requests
from django.conf import settings

def get_github_auth_url():
    client_id = settings.GITHUB_CLIENT_ID
    redirect_uri = "http://127.0.0.1:8000/github/callback/"
    scope = "repo,user,read:org"
    return f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"

def get_access_token(code):
    url = "https://github.com/login/oauth/access_token"
    payload = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    response = requests.post(url, data=payload, headers=headers)
    return response.json().get('access_token')

def fetch_github_user(access_token):
    url = "https://api.github.com/user"
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(url, headers=headers)
    return response.json()

def fetch_github_stats(access_token, username, repo_name=None):
    headers = {
        'Authorization': f'token {access_token}', 
        'Accept': 'application/vnd.github.v3+json',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    base_query = f"author:{username}"
    if repo_name:
        base_query += f" repo:{username}/{repo_name}"
        
    def _get_data(query):
        import time
        # Add timestamp to query to bust GitHub Search API cache
        url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&_={int(time.time())}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('total_count', 0), data.get('items', [])
        else:
            print(f"Error fetching GitHub data: {resp.status_code} - {resp.text}")
        return 0, []

    total_prs, pr_items = _get_data(f"type:pr {base_query}")
    merged_prs, _ = _get_data(f"type:pr is:merged {base_query}")
    open_prs, _ = _get_data(f"type:pr is:open {base_query}")
    closed_prs, _ = _get_data(f"type:pr is:closed -is:merged {base_query}")
    total_issues, issue_items = _get_data(f"type:issue {base_query}")
    resolved_issues, _ = _get_data(f"type:issue is:closed {base_query}")
    
    # Process PR items for the template
    detailed_prs = []
    for item in pr_items[:20]: # Limit to 20 recent
        # Extract repo name from repository_url
        repo_full_name = item.get('repository_url', '').split('/')[-1]
        
        state = 'open'
        if item.get('pull_request', {}).get('merged_at'):
            state = 'merged'
        elif item.get('state') == 'closed':
            state = 'closed'
            
        detailed_prs.append({
            'title': item.get('title'),
            'state': state,
            'repo': repo_full_name,
            'created_at': item.get('created_at'),
            'url': item.get('html_url'),
        })

    return {
        'total_prs': total_prs,
        'merged_prs': merged_prs,
        'open_prs': open_prs,
        'closed_prs': closed_prs,
        'total_issues': total_issues,
        'resolved_issues': resolved_issues,
        'detailed_prs': detailed_prs,
    }

def fetch_github_repos(access_token):
    url = "https://api.github.com/user/repos?per_page=100"
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(url, headers=headers)
    return response.json()

def calculate_productivity_score(stats):
    # Simple score: (merged_prs * 10) + (resolved_issues * 5)
    # This can be adjusted/balanced
    score = (stats['merged_prs'] * 10) + (stats['resolved_issues'] * 5)
    return float(score)
