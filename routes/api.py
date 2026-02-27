"""
REST API routes for programmatic access.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db, limiter, csrf
from models import (User, Project, Issue, Comment, IssueStatus, IssuePriority,
                    UserRole, Epic, Component, Version, Sprint, Label)

api_bp = Blueprint('api', __name__)

# Exempt API routes from CSRF (they use token auth)
csrf.exempt(api_bp)


def issue_to_dict(issue):
    """Convert issue to dictionary."""
    return {
        'id': issue.id,
        'key': issue.key,
        'title': issue.title,
        'description': issue.description,
        'status': issue.status.value,
        'priority': issue.priority.value,
        'type': issue.issue_type,
        'project': {
            'id': issue.project_id,
            'key': issue.project.key,
            'name': issue.project.name
        },
        'reporter': {
            'id': issue.reporter_id,
            'username': issue.reporter.username
        } if issue.reporter else None,
        'assignee': {
            'id': issue.assignee_id,
            'username': issue.assignee.username
        } if issue.assignee else None,
        'due_date': issue.due_date.isoformat() if issue.due_date else None,
        'created_at': issue.created_at.isoformat(),
        'updated_at': issue.updated_at.isoformat(),
        'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in issue.labels],
        'github_pr_url': issue.github_pr_url,
        'github_pr_status': issue.github_pr_status
    }


def project_to_dict(project):
    """Convert project to dictionary."""
    return {
        'id': project.id,
        'key': project.key,
        'name': project.name,
        'description': project.description,
        'color': project.color,
        'is_active': project.is_active,
        'is_public': project.is_public,
        'owner': {
            'id': project.owner_id,
            'username': project.owner.username
        },
        'issue_count': project.issue_count,
        'open_issues_count': project.open_issues_count,
        'created_at': project.created_at.isoformat(),
        'github_repo': project.github_repo,
        'github_enabled': project.github_enabled
    }


def user_to_dict(user):
    """Convert user to dictionary."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'role': user.role.value,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat()
    }


# -------------------- Issues API --------------------

@api_bp.route('/issues', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def list_issues():
    """List issues with optional filters."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    priority = request.args.get('priority')
    project_id = request.args.get('project_id', type=int)
    assignee_id = request.args.get('assignee_id', type=int)
    
    query = Issue.query
    
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    if status:
        try:
            query = query.filter(Issue.status == IssueStatus(status))
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if priority:
        try:
            query = query.filter(Issue.priority == IssuePriority(priority))
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400
    
    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)
    
    pagination = query.order_by(Issue.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'issues': [issue_to_dict(i) for i in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@api_bp.route('/issues/<int:issue_id>', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_issue(issue_id):
    """Get issue details."""
    issue = Issue.query.get_or_404(issue_id)
    return jsonify(issue_to_dict(issue))


@api_bp.route('/issues', methods=['POST'])
@login_required
@limiter.limit("30/minute")
def create_issue():
    """Create a new issue."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    project_id = data.get('project_id')
    title = data.get('title', '').strip()
    
    if not project_id or not title:
        return jsonify({'error': 'project_id and title are required'}), 400
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    issue = Issue(
        project_id=project_id,
        number=project.generate_issue_number(),
        title=title,
        description=data.get('description', ''),
        reporter_id=current_user.id,
        status=IssueStatus.BACKLOG
    )
    
    # Optional fields
    if data.get('priority'):
        try:
            issue.priority = IssuePriority(data['priority'])
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400
    
    if data.get('assignee_id'):
        issue.assignee_id = data['assignee_id']
    
    if data.get('issue_type'):
        issue.issue_type = data['issue_type']
    
    if data.get('due_date'):
        try:
            issue.due_date = datetime.fromisoformat(data['due_date'])
        except ValueError:
            return jsonify({'error': 'Invalid due_date format'}), 400
    
    db.session.add(issue)
    db.session.commit()
    
    return jsonify(issue_to_dict(issue)), 201


@api_bp.route('/issues/<int:issue_id>', methods=['PUT', 'PATCH'])
@login_required
@limiter.limit("30/minute")
def update_issue(issue_id):
    """Update an issue."""
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'title' in data:
        issue.title = data['title'].strip()
    
    if 'description' in data:
        issue.description = data['description']
    
    if 'status' in data:
        try:
            issue.status = IssueStatus(data['status'])
            if issue.status == IssueStatus.DONE and not issue.resolved_at:
                issue.resolved_at = datetime.utcnow()
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if 'priority' in data:
        try:
            issue.priority = IssuePriority(data['priority'])
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400
    
    if 'assignee_id' in data:
        issue.assignee_id = data['assignee_id']
    
    if 'due_date' in data:
        if data['due_date']:
            try:
                issue.due_date = datetime.fromisoformat(data['due_date'])
            except ValueError:
                return jsonify({'error': 'Invalid due_date format'}), 400
        else:
            issue.due_date = None
    
    db.session.commit()
    
    return jsonify(issue_to_dict(issue))


@api_bp.route('/issues/<int:issue_id>', methods=['DELETE'])
@login_required
@limiter.limit("10/minute")
def delete_issue(issue_id):
    """Delete an issue."""
    issue = Issue.query.get_or_404(issue_id)
    
    if not (current_user.is_admin() or issue.reporter_id == current_user.id):
        return jsonify({'error': 'Permission denied'}), 403
    
    db.session.delete(issue)
    db.session.commit()
    
    return jsonify({'message': 'Issue deleted successfully'})


@api_bp.route('/issues/<int:issue_id>/comments', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_comments(issue_id):
    """Get comments for an issue."""
    issue = Issue.query.get_or_404(issue_id)
    comments = issue.comments.order_by(Comment.created_at.asc()).all()
    
    return jsonify({
        'comments': [{
            'id': c.id,
            'content': c.content,
            'author': {
                'id': c.author_id,
                'username': c.author.username
            },
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat()
        } for c in comments]
    })


@api_bp.route('/issues/<int:issue_id>/comments', methods=['POST'])
@login_required
@limiter.limit("30/minute")
def add_comment(issue_id):
    """Add a comment to an issue."""
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    comment = Comment(
        issue_id=issue_id,
        author_id=current_user.id,
        content=data['content'].strip()
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'id': comment.id,
        'content': comment.content,
        'author': {
            'id': comment.author_id,
            'username': comment.author.username
        },
        'created_at': comment.created_at.isoformat()
    }), 201


# -------------------- Projects API --------------------

@api_bp.route('/projects', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def list_projects():
    """List projects user has access to."""
    if current_user.is_admin():
        projects = Project.query.all()
    else:
        projects = Project.query.filter(
            (Project.owner_id == current_user.id) |
            (Project.is_public == True) |
            (Project.members.any(id=current_user.id))
        ).all()
    
    return jsonify({
        'projects': [project_to_dict(p) for p in projects]
    })


@api_bp.route('/projects/<int:project_id>', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project(project_id):
    """Get project details."""
    project = Project.query.get_or_404(project_id)
    return jsonify(project_to_dict(project))


@api_bp.route('/projects/<int:project_id>/epics', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_epics(project_id):
    """Get epics for a project."""
    project = Project.query.get_or_404(project_id)
    epics = Epic.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'epics': [{
            'id': epic.id,
            'name': epic.name,
            'description': epic.description,
            'color': epic.color,
            'status': epic.status,
            'progress': epic.progress
        } for epic in epics]
    })


@api_bp.route('/projects/<int:project_id>/sprints', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_sprints(project_id):
    """Get sprints for a project."""
    project = Project.query.get_or_404(project_id)
    sprints = Sprint.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'sprints': [{
            'id': sprint.id,
            'name': sprint.name,
            'goal': sprint.goal,
            'status': sprint.status,
            'start_date': sprint.start_date.isoformat() if sprint.start_date else None,
            'end_date': sprint.end_date.isoformat() if sprint.end_date else None
        } for sprint in sprints]
    })


@api_bp.route('/projects/<int:project_id>/versions', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_versions(project_id):
    """Get versions for a project."""
    project = Project.query.get_or_404(project_id)
    versions = Version.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'versions': [{
            'id': version.id,
            'name': version.name,
            'description': version.description,
            'status': version.status,
            'release_date': version.release_date.isoformat() if version.release_date else None,
            'progress': version.progress
        } for version in versions]
    })


@api_bp.route('/projects/<int:project_id>/components', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_components(project_id):
    """Get components for a project."""
    project = Project.query.get_or_404(project_id)
    components = Component.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'components': [{
            'id': component.id,
            'name': component.name,
            'description': component.description,
            'lead': {
                'id': component.lead.id,
                'username': component.lead.username
            } if component.lead else None
        } for component in components]
    })


@api_bp.route('/projects/<int:project_id>/labels', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_labels(project_id):
    """Get labels for a project."""
    project = Project.query.get_or_404(project_id)
    labels = Label.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'labels': [{
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'description': label.description
        } for label in labels]
    })


@api_bp.route('/projects/<int:project_id>/members', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_members(project_id):
    """Get members of a project."""
    project = Project.query.get_or_404(project_id)
    
    # Get all unique members (owner + assigned members)
    members_set = set([project.owner])
    members_set.update(project.members)
    
    return jsonify({
        'members': [{
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'full_name': member.full_name
        } for member in sorted(members_set, key=lambda m: m.username)]
    })


@api_bp.route('/projects/<int:project_id>/issues', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_project_issues(project_id):
    """Get issues for a project."""
    project = Project.query.get_or_404(project_id)
    issues = Issue.query.filter_by(project_id=project_id).all()
    
    return jsonify({
        'issues': [{
            'id': issue.id,
            'identifier': issue.identifier,
            'title': issue.title,
            'issue_type': issue.issue_type.value if hasattr(issue.issue_type, 'value') else str(issue.issue_type),
            'status': issue.status.value,
            'priority': issue.priority.value
        } for issue in issues]
    })


# -------------------- Users API --------------------

@api_bp.route('/users', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def list_users():
    """List active users."""
    users = User.query.filter_by(is_active=True).all()
    return jsonify({
        'users': [user_to_dict(u) for u in users]
    })


@api_bp.route('/users/me', methods=['GET'])
@login_required
@limiter.limit("60/minute")
def get_current_user():
    """Get current user details."""
    return jsonify(user_to_dict(current_user))


# -------------------- Webhook for GitHub --------------------

@api_bp.route('/webhook/github', methods=['POST'])
@limiter.limit("100/minute")
def github_webhook():
    """Handle GitHub webhook events."""
    event = request.headers.get('X-GitHub-Event')
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data'}), 400
    
    if event == 'pull_request':
        action = data.get('action')
        pr = data.get('pull_request', {})
        pr_url = pr.get('html_url')
        pr_state = pr.get('state')
        pr_merged = pr.get('merged', False)
        
        # Find issues linked to this PR
        issues = Issue.query.filter_by(github_pr_url=pr_url).all()
        
        for issue in issues:
            if pr_merged:
                issue.github_pr_status = 'merged'
                # Optionally auto-close issue
                if issue.status != IssueStatus.DONE:
                    issue.status = IssueStatus.DONE
                    issue.resolved_at = datetime.utcnow()
            elif pr_state == 'closed':
                issue.github_pr_status = 'closed'
            elif pr_state == 'open':
                issue.github_pr_status = 'open'
        
        db.session.commit()
    
    return jsonify({'status': 'ok'})


# -------------------- GitHub User API --------------------

from services.github_service import (
    get_user_repos, get_user_orgs, get_org_repos,
    get_repo_issues, get_repo_prs, get_repo_branches,
    get_repo_commits, create_github_issue, get_github_user
)


@api_bp.route('/github/repos', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_repos():
    """Get repositories for the authenticated user."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    repos = get_user_repos(current_user.github_access_token, page, per_page)
    
    if repos is None:
        return jsonify({'error': 'Failed to fetch repositories'}), 500
    
    return jsonify({
        'repos': [{
            'id': r['id'],
            'name': r['name'],
            'full_name': r['full_name'],
            'description': r['description'],
            'private': r['private'],
            'html_url': r['html_url'],
            'language': r.get('language'),
            'stargazers_count': r.get('stargazers_count', 0),
            'open_issues_count': r.get('open_issues_count', 0),
            'updated_at': r.get('updated_at')
        } for r in repos],
        'page': page
    })


@api_bp.route('/github/orgs', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_orgs():
    """Get organizations for the authenticated user."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    orgs = get_user_orgs(current_user.github_access_token)
    
    if orgs is None:
        return jsonify({'error': 'Failed to fetch organizations'}), 500
    
    return jsonify({
        'orgs': [{
            'id': o['id'],
            'login': o['login'],
            'description': o.get('description'),
            'avatar_url': o.get('avatar_url')
        } for o in orgs]
    })


@api_bp.route('/github/repos/<owner>/<repo>/issues', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_repo_issues(owner, repo):
    """Get issues for a specific repository."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    state = request.args.get('state', 'open')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    issues = get_repo_issues(current_user.github_access_token, owner, repo, state, page, per_page)
    
    if issues is None:
        return jsonify({'error': 'Failed to fetch issues'}), 500
    
    return jsonify({
        'issues': [{
            'id': i['id'],
            'number': i['number'],
            'title': i['title'],
            'state': i['state'],
            'html_url': i['html_url'],
            'user': i['user']['login'] if i.get('user') else None,
            'labels': [{'name': l['name'], 'color': l['color']} for l in i.get('labels', [])],
            'assignees': [a['login'] for a in i.get('assignees', [])],
            'created_at': i.get('created_at'),
            'updated_at': i.get('updated_at')
        } for i in issues if 'pull_request' not in i],  # Filter out PRs
        'page': page
    })


@api_bp.route('/github/repos/<owner>/<repo>/pulls', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_repo_pulls(owner, repo):
    """Get pull requests for a specific repository."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    state = request.args.get('state', 'open')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    prs = get_repo_prs(current_user.github_access_token, owner, repo, state, page, per_page)
    
    if prs is None:
        return jsonify({'error': 'Failed to fetch pull requests'}), 500
    
    return jsonify({
        'pull_requests': [{
            'id': pr['id'],
            'number': pr['number'],
            'title': pr['title'],
            'state': pr['state'],
            'html_url': pr['html_url'],
            'user': pr['user']['login'] if pr.get('user') else None,
            'head': pr['head']['ref'] if pr.get('head') else None,
            'base': pr['base']['ref'] if pr.get('base') else None,
            'draft': pr.get('draft', False),
            'mergeable': pr.get('mergeable'),
            'created_at': pr.get('created_at'),
            'updated_at': pr.get('updated_at')
        } for pr in prs],
        'page': page
    })


@api_bp.route('/github/repos/<owner>/<repo>/branches', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_repo_branches(owner, repo):
    """Get branches for a specific repository."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    branches = get_repo_branches(current_user.github_access_token, owner, repo)
    
    if branches is None:
        return jsonify({'error': 'Failed to fetch branches'}), 500
    
    return jsonify({
        'branches': [{
            'name': b['name'],
            'protected': b.get('protected', False)
        } for b in branches]
    })


@api_bp.route('/github/repos/<owner>/<repo>/commits', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_repo_commits(owner, repo):
    """Get recent commits for a specific repository."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    branch = request.args.get('branch', 'main')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    commits = get_repo_commits(current_user.github_access_token, owner, repo, branch, page, per_page)
    
    if commits is None:
        return jsonify({'error': 'Failed to fetch commits'}), 500
    
    return jsonify({
        'commits': [{
            'sha': c['sha'],
            'message': c['commit']['message'],
            'author': c['commit']['author']['name'] if c.get('commit', {}).get('author') else None,
            'date': c['commit']['author']['date'] if c.get('commit', {}).get('author') else None,
            'html_url': c['html_url']
        } for c in commits],
        'page': page
    })


@api_bp.route('/github/user', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def github_user_profile():
    """Get current user's GitHub profile."""
    if not current_user.github_access_token:
        return jsonify({'error': 'GitHub account not connected'}), 401
    
    user = get_github_user(current_user.github_access_token)
    
    if user is None:
        return jsonify({'error': 'Failed to fetch GitHub profile'}), 500
    
    return jsonify({
        'id': user['id'],
        'login': user['login'],
        'name': user.get('name'),
        'email': user.get('email'),
        'avatar_url': user.get('avatar_url'),
        'html_url': user.get('html_url'),
        'public_repos': user.get('public_repos', 0),
        'followers': user.get('followers', 0)
    })


@api_bp.route('/github/connected', methods=['GET'])
@login_required
def github_connected():
    """Check if GitHub is connected for current user."""
    return jsonify({
        'connected': bool(current_user.github_access_token),
        'github_id': current_user.github_id,
        'oauth_provider': current_user.oauth_provider
    })


# -------------------- AI Generation API --------------------

@api_bp.route('/ai/generate-issue', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def ai_generate_issue():
    """Generate issue content using AWS Bedrock AI."""
    from services.bedrock_service import generate_issue_content, is_bedrock_configured
    
    if not is_bedrock_configured():
        return jsonify({'error': 'AI service not configured'}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    issue_type = data.get('issue_type', 'task')
    context = data.get('context', '')
    
    result = generate_issue_content(prompt, issue_type, context)
    
    if result:
        return jsonify({
            'success': True,
            'data': result
        })
    else:
        return jsonify({'error': 'Failed to generate content. Please try again.'}), 500


@api_bp.route('/ai/enhance-description', methods=['POST'])
@login_required
@limiter.limit("15/minute")
def ai_enhance_description():
    """Enhance an existing description using AI."""
    from services.bedrock_service import enhance_description, is_bedrock_configured
    
    if not is_bedrock_configured():
        return jsonify({'error': 'AI service not configured'}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    description = data.get('description', '').strip()
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    
    issue_type = data.get('issue_type', 'task')
    
    result = enhance_description(description, issue_type)
    
    if result:
        return jsonify({
            'success': True,
            'enhanced_description': result
        })
    else:
        return jsonify({'error': 'Failed to enhance description'}), 500


@api_bp.route('/ai/suggest-criteria', methods=['POST'])
@login_required
@limiter.limit("15/minute")
def ai_suggest_criteria():
    """Suggest acceptance criteria based on title and description."""
    from services.bedrock_service import suggest_acceptance_criteria, is_bedrock_configured
    
    if not is_bedrock_configured():
        return jsonify({'error': 'AI service not configured'}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    
    if not title and not description:
        return jsonify({'error': 'Title or description required'}), 400
    
    issue_type = data.get('issue_type', 'feature')
    
    result = suggest_acceptance_criteria(title, description, issue_type)
    
    if result:
        return jsonify({
            'success': True,
            'acceptance_criteria': result
        })
    else:
        return jsonify({'error': 'Failed to generate acceptance criteria'}), 500


@api_bp.route('/ai/status', methods=['GET'])
@login_required
def ai_status():
    """Check if AI service is available."""
    from services.bedrock_service import is_bedrock_configured
    
    return jsonify({
        'available': is_bedrock_configured()
    })


# -------------------- GitHub Integration API --------------------

@api_bp.route('/issues/<int:issue_id>/github/discover-branch', methods=['POST'])
@login_required
@limiter.limit("30/minute")
def discover_issue_branch(issue_id):
    """Discover and link GitHub branch for an issue."""
    from services.github_service import find_branch_for_issue
    
    issue = Issue.query.get_or_404(issue_id)
    project = issue.project
    
    if not project.github_repo:
        return jsonify({'error': 'GitHub repository not configured for this project'}), 400
    
    # Check if user has GitHub token
    user_token = current_user.github_access_token
    if not user_token:
        return jsonify({'error': 'Please log in with GitHub to use branch discovery'}), 400
    
    # Parse owner/repo
    parts = project.github_repo.split('/')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid GitHub repository format'}), 400
    
    owner, repo = parts
    
    # Find branch using user's token
    branch_info = find_branch_for_issue(owner, repo, issue.key, user_token)
    
    # Check for access restriction error
    if isinstance(branch_info, dict) and branch_info.get('error') == 'access_restricted':
        return jsonify({
            'success': False,
            'error': 'access_restricted',
            'message': 'Organization has OAuth access restrictions. An admin must approve this app in organization settings.'
        }), 403
    
    if branch_info:
        issue.github_branch = branch_info['name']
        
        # Auto-populate PR URL and commit SHA if found
        if branch_info.get('pr_url'):
            issue.github_pr_url = branch_info['pr_url']
            issue.github_pr_status = branch_info.get('pr_state', 'open')
        
        if branch_info.get('full_sha'):
            issue.github_commit_sha = branch_info['full_sha']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'branch': {
                'name': branch_info['name'],
                'sha': branch_info.get('sha', ''),
                'url': f"https://github.com/{owner}/{repo}/tree/{branch_info['name']}",
                'pr_url': branch_info.get('pr_url'),
                'pr_state': branch_info.get('pr_state'),
                'commit_sha': branch_info.get('full_sha', '')
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': f'No branch found matching {issue.key}'
        })


@api_bp.route('/projects/<int:project_id>/github/discover-branches', methods=['POST'])
@login_required
@limiter.limit("15/minute")
def discover_project_branches(project_id):
    """Discover and link GitHub branches for all project issues."""
    from services.github_service import discover_branches_for_issues
    
    project = Project.query.get_or_404(project_id)
    
    if not project.github_repo:
        return jsonify({'error': 'GitHub repository not configured for this project'}), 400
    
    # Check if user has GitHub token
    user_token = current_user.github_access_token
    if not user_token:
        return jsonify({'error': 'Please log in with GitHub to use branch discovery'}), 400
    
    # Parse owner/repo
    parts = project.github_repo.split('/')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid GitHub repository format'}), 400
    
    owner, repo = parts
    
    # Get all open issues for the project
    issues = Issue.query.filter_by(project_id=project_id).filter(
        Issue.status != IssueStatus.DONE
    ).all()
    
    # Discover branches using user's token
    discovered = discover_branches_for_issues(owner, repo, issues, user_token)
    
    # Update issues with discovered branches
    updated_count = 0
    for issue_id, branch_info in discovered.items():
        issue = Issue.query.get(issue_id)
        if issue and not issue.github_branch:  # Only update if not already set
            issue.github_branch = branch_info['branch_name']
            
            # Auto-populate PR URL and commit SHA if found
            if branch_info.get('pr_url'):
                issue.github_pr_url = branch_info['pr_url']
                issue.github_pr_status = branch_info.get('pr_state', 'open')
            
            if branch_info.get('full_sha'):
                issue.github_commit_sha = branch_info['full_sha']
            
            updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'discovered': len(discovered),
        'updated': updated_count,
        'branches': discovered
    })


@api_bp.route('/issues/<int:issue_id>/github/unlink-branch', methods=['POST'])
@login_required
def unlink_issue_branch(issue_id):
    """Unlink GitHub branch from an issue."""
    issue = Issue.query.get_or_404(issue_id)
    
    issue.github_branch = None
    db.session.commit()
    
    return jsonify({'success': True})
