"""
Dashboard routes for user and admin dashboards.
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_
from extensions import db
from models import (User, Project, Issue, Comment, IssueStatus, IssuePriority,
                    UserRole, project_members)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """User dashboard - main overview."""
    if not current_user.current_organization_id:
        return redirect(url_for('organization.signup'))
    
    # Get user's assigned issues (within current organization)
    assigned_issues = Issue.query.join(Project).filter(
        Project.organization_id == current_user.current_organization_id,
        Issue.assignee_id == current_user.id,
        Issue.status != IssueStatus.DONE
    ).order_by(Issue.priority.desc(), Issue.due_date.asc()).limit(10).all()
    
    # Get overdue issues
    overdue_issues = Issue.query.join(Project).filter(
        Project.organization_id == current_user.current_organization_id,
        Issue.assignee_id == current_user.id,
        Issue.due_date < datetime.utcnow(),
        Issue.status != IssueStatus.DONE
    ).order_by(Issue.due_date.asc()).all()
    
    # Get recently updated issues
    recent_issues = Issue.query.join(Project).filter(
        Project.organization_id == current_user.current_organization_id,
        (Issue.assignee_id == current_user.id) | (Issue.reporter_id == current_user.id)
    ).order_by(Issue.updated_at.desc()).limit(5).all()
    
    # Get user's projects (filtered by organization)
    user_projects = Project.query.filter(
        Project.organization_id == current_user.current_organization_id,
        (Project.owner_id == current_user.id) | (Project.members.any(id=current_user.id))
    ).limit(5).all()
    
    # Activity feed - recent comments (within organization)
    recent_comments = Comment.query.join(Issue).join(Project).filter(
        Project.organization_id == current_user.current_organization_id,
        Comment.author_id == current_user.id
    ).order_by(Comment.created_at.desc()).limit(5).all()
    
    # Stats (filtered by organization)
    stats = {
        'assigned': Issue.query.join(Project).filter(
            Project.organization_id == current_user.current_organization_id,
            Issue.assignee_id == current_user.id,
            Issue.status != IssueStatus.DONE
        ).count(),
        'overdue': len(overdue_issues),
        'completed_this_week': Issue.query.join(Project).filter(
            Project.organization_id == current_user.current_organization_id,
            Issue.assignee_id == current_user.id,
            Issue.status == IssueStatus.DONE,
            Issue.resolved_at >= datetime.utcnow() - timedelta(days=7)
        ).count(),
        'in_progress': Issue.query.join(Project).filter(
            Project.organization_id == current_user.current_organization_id,
            Issue.assignee_id == current_user.id,
            Issue.status == IssueStatus.IN_PROGRESS
        ).count()
    }
    
    # Task distribution for pie chart (filtered by organization)
    task_distribution = {
        'backlog': Issue.query.join(Project).filter(Project.organization_id == current_user.current_organization_id, Issue.assignee_id == current_user.id, Issue.status == IssueStatus.BACKLOG).count(),
        'todo': Issue.query.join(Project).filter(Project.organization_id == current_user.current_organization_id, Issue.assignee_id == current_user.id, Issue.status == IssueStatus.TODO).count(),
        'in_progress': Issue.query.join(Project).filter(Project.organization_id == current_user.current_organization_id, Issue.assignee_id == current_user.id, Issue.status == IssueStatus.IN_PROGRESS).count(),
        'code_review': Issue.query.join(Project).filter(Project.organization_id == current_user.current_organization_id, Issue.assignee_id == current_user.id, Issue.status == IssueStatus.CODE_REVIEW).count(),
        'done': Issue.query.join(Project).filter(
            Project.organization_id == current_user.current_organization_id,
            Issue.assignee_id == current_user.id,
            Issue.status == IssueStatus.DONE,
            Issue.resolved_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
    }
    
    return render_template('dashboard/index.html',
                          assigned_issues=assigned_issues,
                          overdue_issues=overdue_issues,
                          recent_issues=recent_issues,
                          user_projects=user_projects,
                          recent_comments=recent_comments,
                          stats=stats,
                          task_distribution=task_distribution)


@dashboard_bp.route('/weekly-stats')
@login_required
def weekly_stats():
    """Get weekly completion stats for chart."""
    stats = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        completed = Issue.query.filter_by(assignee_id=current_user.id)\
            .filter(Issue.status == IssueStatus.DONE)\
            .filter(and_(Issue.resolved_at >= day_start, Issue.resolved_at <= day_end))\
            .count()
        
        stats.append({
            'date': day.strftime('%a'),
            'completed': completed
        })
    
    return jsonify(stats)


@dashboard_bp.route('/my-issues')
@login_required
def my_issues():
    """View all issues assigned to current user."""
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    query = Issue.query.filter_by(assignee_id=current_user.id)
    
    if status_filter != 'all':
        query = query.filter(Issue.status == IssueStatus(status_filter))
    
    if priority_filter != 'all':
        query = query.filter(Issue.priority == IssuePriority(priority_filter))
    
    issues = query.order_by(Issue.priority.desc(), Issue.due_date.asc()).all()
    
    return render_template('dashboard/my_issues.html',
                          issues=issues,
                          status_filter=status_filter,
                          priority_filter=priority_filter)


@dashboard_bp.route('/activity')
@login_required
def activity():
    """View user's activity feed."""
    from models import AuditLog
    
    activities = AuditLog.query.filter_by(user_id=current_user.id)\
        .order_by(AuditLog.created_at.desc())\
        .limit(50).all()
    
    return render_template('dashboard/activity.html', activities=activities)


# Need to import request for query params
from flask import request
