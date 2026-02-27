"""
GitHub integration service for repository linking.
Supports both app-level token and user OAuth tokens.
"""
import re
import requests
from flask import current_app
from models import Settings


def get_github_token():
    """Get GitHub token from settings or config."""
    token = Settings.get('github_token')
    if not token:
        token = current_app.config.get('GITHUB_TOKEN')
    return token


def is_github_enabled():
    """Check if GitHub integration is enabled."""
    enabled = Settings.get('github_enabled', 'false').lower() == 'true'
    if not enabled:
        enabled = current_app.config.get('GITHUB_ENABLED', False)
    return enabled


def make_github_request(endpoint, method='GET', data=None, token=None):
    """Make authenticated request to GitHub API.
    
    Args:
        endpoint: GitHub API endpoint (e.g., '/user/repos')
        method: HTTP method (GET, POST, PATCH)
        data: JSON data for POST/PATCH requests
        token: User's OAuth token (uses app token if not provided)
    """
    if not token:
        token = get_github_token()
    
    if not token:
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'ProjectFlow-App'
    }
    
    url = f'https://api.github.com{endpoint}'
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data, timeout=10)
        else:
            return None
        
        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 403:
            error_msg = response.json().get('message', response.text)
            current_app.logger.error(f'GitHub API 403 Forbidden: {error_msg}')
            return {'error': 'access_restricted', 'message': error_msg}
        else:
            current_app.logger.error(f'GitHub API error: {response.status_code} - {response.text}')
            return None
    except requests.RequestException as e:
        current_app.logger.error(f'GitHub request failed: {e}')
        return None


# ============================================
# User-specific GitHub API functions
# (Use user's OAuth token from login)
# ============================================

def get_user_repos(user_token, page=1, per_page=30):
    """Get repositories accessible to the authenticated user."""
    return make_github_request(
        f'/user/repos?sort=updated&per_page={per_page}&page={page}',
        token=user_token
    )


def get_user_orgs(user_token):
    """Get organizations the user belongs to."""
    return make_github_request('/user/orgs', token=user_token)


def get_org_repos(user_token, org, page=1, per_page=30):
    """Get repositories for an organization."""
    return make_github_request(
        f'/orgs/{org}/repos?sort=updated&per_page={per_page}&page={page}',
        token=user_token
    )


def get_repo_issues(user_token, owner, repo, state='open', page=1, per_page=30):
    """Get issues for a repository."""
    return make_github_request(
        f'/repos/{owner}/{repo}/issues?state={state}&per_page={per_page}&page={page}',
        token=user_token
    )


def get_repo_prs(user_token, owner, repo, state='open', page=1, per_page=30):
    """Get pull requests for a repository."""
    return make_github_request(
        f'/repos/{owner}/{repo}/pulls?state={state}&per_page={per_page}&page={page}',
        token=user_token
    )


def get_pull_request_by_branch(user_token, owner, repo, branch_name):
    """Get pull request for a specific branch.
    
    Args:
        user_token: User's GitHub OAuth token
        owner: Repository owner
        repo: Repository name
        branch_name: Branch name to find PR for
        
    Returns:
        PR info dict or None if no PR found
    """
    # Get open PRs
    prs = get_repo_prs(user_token, owner, repo, state='open')
    if prs and isinstance(prs, list):
        for pr in prs:
            if pr.get('head', {}).get('ref') == branch_name:
                return {
                    'url': pr.get('html_url'),
                    'number': pr.get('number'),
                    'state': pr.get('state'),
                    'title': pr.get('title')
                }
    
    # Check closed/merged PRs
    prs = get_repo_prs(user_token, owner, repo, state='closed')
    if prs and isinstance(prs, list):
        for pr in prs:
            if pr.get('head', {}).get('ref') == branch_name:
                merged = pr.get('merged_at') is not None
                return {
                    'url': pr.get('html_url'),
                    'number': pr.get('number'),
                    'state': 'merged' if merged else 'closed',
                    'title': pr.get('title')
                }
    
    return None


def get_repo_prs(user_token, owner, repo, state='open', page=1, per_page=30):
    """Get pull requests for a repository."""
    return make_github_request(
        f'/repos/{owner}/{repo}/pulls?state={state}&per_page={per_page}&page={page}',
        token=user_token
    )


def get_repo_branches(user_token, owner, repo):
    """Get branches for a repository."""
    return make_github_request(
        f'/repos/{owner}/{repo}/branches',
        token=user_token
    )


def get_repo_commits(user_token, owner, repo, branch='main', page=1, per_page=30):
    """Get recent commits for a repository."""
    return make_github_request(
        f'/repos/{owner}/{repo}/commits?sha={branch}&per_page={per_page}&page={page}',
        token=user_token
    )


def create_github_issue(user_token, owner, repo, title, body=None, labels=None, assignees=None):
    """Create an issue in a GitHub repository."""
    data = {'title': title}
    if body:
        data['body'] = body
    if labels:
        data['labels'] = labels
    if assignees:
        data['assignees'] = assignees
    
    return make_github_request(
        f'/repos/{owner}/{repo}/issues',
        method='POST',
        data=data,
        token=user_token
    )


def get_github_user(user_token):
    """Get authenticated user's profile."""
    return make_github_request('/user', token=user_token)


def get_repo_info(owner, repo):
    """Get repository information."""
    if not is_github_enabled():
        return None
    
    return make_github_request(f'/repos/{owner}/{repo}')


def get_pull_request(owner, repo, pr_number):
    """Get pull request details."""
    if not is_github_enabled():
        return None
    
    return make_github_request(f'/repos/{owner}/{repo}/pulls/{pr_number}')


def get_commit(owner, repo, sha):
    """Get commit details."""
    if not is_github_enabled():
        return None
    
    return make_github_request(f'/repos/{owner}/{repo}/commits/{sha}')


def get_pr_commits(owner, repo, pr_number):
    """Get commits from a pull request."""
    if not is_github_enabled():
        return None
    
    return make_github_request(f'/repos/{owner}/{repo}/pulls/{pr_number}/commits')


def link_github_pr(repo_url, pr_url):
    """Link a GitHub PR to an issue and return PR status."""
    if not is_github_enabled():
        return None
    
    # Parse PR URL to get owner, repo, and PR number
    # Format: https://github.com/owner/repo/pull/123
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    
    if not match:
        return None
    
    owner, repo, pr_number = match.groups()
    
    pr_data = get_pull_request(owner, repo, int(pr_number))
    
    if pr_data:
        state = pr_data.get('state')
        merged = pr_data.get('merged', False)
        
        if merged:
            return 'merged'
        return state
    
    return None


def get_recent_commits(owner, repo, limit=10):
    """Get recent commits from a repository."""
    if not is_github_enabled():
        return []
    
    commits = make_github_request(f'/repos/{owner}/{repo}/commits?per_page={limit}')
    
    if commits:
        return [{
            'sha': c.get('sha', '')[:7],
            'message': c.get('commit', {}).get('message', '').split('\n')[0],
            'author': c.get('commit', {}).get('author', {}).get('name', 'Unknown'),
            'date': c.get('commit', {}).get('author', {}).get('date', ''),
            'url': c.get('html_url', '')
        } for c in commits]
    
    return []


def get_open_pull_requests(owner, repo):
    """Get open pull requests from a repository."""
    if not is_github_enabled():
        return []
    
    prs = make_github_request(f'/repos/{owner}/{repo}/pulls?state=open')
    
    if prs:
        return [{
            'number': pr.get('number'),
            'title': pr.get('title'),
            'url': pr.get('html_url'),
            'user': pr.get('user', {}).get('login', 'Unknown'),
            'created_at': pr.get('created_at'),
            'draft': pr.get('draft', False)
        } for pr in prs]
    
    return []


def search_issues_by_pr(owner, repo, pr_number):
    """Search for commits in a PR that mention issue keys."""
    commits = get_pr_commits(owner, repo, pr_number)
    
    if not commits:
        return []
    
    # Extract issue keys from commit messages
    # Patterns like: PROJECT-123, Fixes #123, Closes #123
    issue_refs = []
    
    for commit in commits:
        message = commit.get('commit', {}).get('message', '')
        
        # Find project key patterns (e.g., PROJ-123)
        project_refs = re.findall(r'([A-Z]+-\d+)', message)
        issue_refs.extend(project_refs)
        
        # Find GitHub issue references (e.g., #123, fixes #123)
        github_refs = re.findall(r'(?:fixes?|closes?|resolves?)\s*#(\d+)', message, re.I)
        issue_refs.extend([f'#{ref}' for ref in github_refs])
    
    return list(set(issue_refs))


def verify_github_token():
    """Verify if the GitHub token is valid."""
    token = get_github_token()
    
    if not token:
        return False, "No token configured"
    
    result = make_github_request('/user')
    
    if result:
        return True, f"Authenticated as {result.get('login')}"
    
    return False, "Token is invalid or expired"


def find_branch_for_issue(owner, repo, issue_key, user_token=None):
    """Find GitHub branches that match an issue key.
    
    Looks for branches named like:
    - issue-key (e.g., ARA-123)
    - issue-key-description (e.g., ARA-123-add-feature)
    - feature/issue-key (e.g., feature/ARA-123)
    - issue-key/description (e.g., ARA-123/add-feature)
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        issue_key: Issue key to search for
        user_token: User's GitHub OAuth token (optional, uses app token if not provided)
    """
    if not is_github_enabled() and not user_token:
        return None
    
    branches = get_repo_branches(user_token, owner, repo)
    
    if not branches:
        return None
    
    # Check if we got an error response
    if isinstance(branches, dict) and branches.get('error') == 'access_restricted':
        return {'error': 'access_restricted', 'message': branches.get('message', '')}
    
    issue_key_lower = issue_key.lower()
    
    # Find branches that contain the issue key
    matching_branches = []
    
    for branch in branches:
        branch_name = branch.get('name', '')
        branch_lower = branch_name.lower()
        
        # Check if branch name contains the issue key
        if issue_key_lower in branch_lower:
            commit_info = branch.get('commit', {})
            matching_branches.append({
                'name': branch_name,
                'sha': commit_info.get('sha', '')[:7],  # Short SHA
                'full_sha': commit_info.get('sha', ''),  # Full SHA
                'url': commit_info.get('url', '')
            })
    
    # Return the first match with full details
    if matching_branches:
        branch_info = matching_branches[0]
        
        # Try to find associated PR
        pr_info = get_pull_request_by_branch(user_token, owner, repo, branch_info['name'])
        if pr_info:
            branch_info['pr_url'] = pr_info['url']
            branch_info['pr_state'] = pr_info['state']
            branch_info['pr_number'] = pr_info['number']
        
        return branch_info
    
    return None


def discover_branches_for_issues(owner, repo, issues, user_token=None):
    """Discover and link branches for multiple issues.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        issues: List of Issue objects
        user_token: User's GitHub OAuth token (optional, uses app token if not provided)
    
    Returns:
        Dictionary mapping issue IDs to branch info
    """
    if not is_github_enabled() and not user_token:
        return {}
    
    branches = get_repo_branches(user_token, owner, repo)
    
    if not branches:
        return {}
    
    # Create a mapping of issue keys to issue objects
    issue_map = {issue.key.lower(): issue for issue in issues}
    
    # Find matches
    discovered = {}
    
    for branch in branches:
        branch_name = branch.get('name', '')
        branch_lower = branch_name.lower()
        
        # Check each issue key
        for issue_key_lower, issue in issue_map.items():
            if issue_key_lower in branch_lower:
                commit_info = branch.get('commit', {})
                discovered[issue.id] = {
                    'branch_name': branch_name,
                    'sha': commit_info.get('sha', '')[:7],
                    'full_sha': commit_info.get('sha', ''),
                    'url': f"https://github.com/{owner}/{repo}/tree/{branch_name}"
                }
                
                # Try to find associated PR
                pr_info = get_pull_request_by_branch(user_token, owner, repo, branch_name)
                if pr_info:
                    discovered[issue.id]['pr_url'] = pr_info['url']
                    discovered[issue.id]['pr_state'] = pr_info['state']
                
                break
    
    return discovered
