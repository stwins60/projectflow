"""
Admin routes for system administration.
"""
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, Response)
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
import csv
import io
from extensions import db
from models import (User, Project, Issue, Comment, Settings, UserRole,
                    IssueStatus, IssuePriority)

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard with overview statistics."""
    # User stats
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    new_users_this_month = User.query.filter(
        User.created_at >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    # Project stats
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(is_active=True).count()
    
    # Issue stats
    total_issues = Issue.query.count()
    open_issues = Issue.query.filter(Issue.status != IssueStatus.DONE).count()
    critical_issues = Issue.query.filter(
        Issue.priority == IssuePriority.CRITICAL,
        Issue.status != IssueStatus.DONE
    ).count()
    
    issues_by_status = db.session.query(
        Issue.status, func.count(Issue.id)
    ).group_by(Issue.status).all()
    
    issues_by_priority = db.session.query(
        Issue.priority, func.count(Issue.id)
    ).group_by(Issue.priority).all()
    
    # Convert to JSON-serializable format
    issues_by_status_dict = {status.value: count for status, count in issues_by_status}
    issues_by_priority_dict = {priority.value: count for priority, count in issues_by_priority}
    
    # Monthly trend
    monthly_trend = []
    for i in range(5, -1, -1):
        month_start = (datetime.utcnow().replace(day=1) - timedelta(days=30*i)).replace(day=1)
        if i > 0:
            month_end = (datetime.utcnow().replace(day=1) - timedelta(days=30*(i-1))).replace(day=1)
        else:
            month_end = datetime.utcnow() + timedelta(days=1)
        
        created = Issue.query.filter(
            Issue.created_at >= month_start,
            Issue.created_at < month_end
        ).count()
        
        resolved = Issue.query.filter(
            Issue.resolved_at >= month_start,
            Issue.resolved_at < month_end
        ).count()
        
        monthly_trend.append({
            'month': month_start.strftime('%b %Y'),
            'created': created,
            'resolved': resolved
        })
    
    # Team performance (top 5 users by resolved issues)
    top_performers = db.session.query(
        User, func.count(Issue.id).label('resolved_count')
    ).join(Issue, Issue.assignee_id == User.id)\
    .filter(Issue.status == IssueStatus.DONE)\
    .filter(Issue.resolved_at >= datetime.utcnow() - timedelta(days=30))\
    .group_by(User.id)\
    .order_by(func.count(Issue.id).desc())\
    .limit(5).all()
    
    # Recent critical issues
    critical_issues_list = Issue.query.filter(
        Issue.priority == IssuePriority.CRITICAL,
        Issue.status != IssueStatus.DONE
    ).order_by(Issue.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html',
                          total_users=total_users,
                          active_users=active_users,
                          new_users_this_month=new_users_this_month,
                          total_projects=total_projects,
                          active_projects=active_projects,
                          total_issues=total_issues,
                          open_issues=open_issues,
                          critical_issues=critical_issues,
                          issues_by_status=issues_by_status_dict,
                          issues_by_priority=issues_by_priority_dict,
                          monthly_trend=monthly_trend,
                          top_performers=top_performers,
                          critical_issues_list=critical_issues_list)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', 'all')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    if role_filter != 'all':
        try:
            query = query.filter(User.role == UserRole(role_filter))
        except ValueError:
            pass
    
    users = query.order_by(User.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html',
                          users=users,
                          search=search,
                          role_filter=role_filter,
                          roles=UserRole)


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details."""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.role = UserRole(request.form.get('role', 'developer'))
        user.is_active = request.form.get('is_active') == 'on'
        user.is_verified = request.form.get('is_verified') == 'on'
        
        # Reset password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', user=user, roles=UserRole)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Application settings page."""
    if request.method == 'POST':
        # SMTP settings
        Settings.set('smtp_server', request.form.get('smtp_server', ''))
        Settings.set('smtp_port', request.form.get('smtp_port', '587'))
        Settings.set('smtp_username', request.form.get('smtp_username', ''))
        Settings.set('smtp_password', request.form.get('smtp_password', ''), encrypted=True)
        Settings.set('smtp_use_tls', request.form.get('smtp_use_tls', 'true'))
        Settings.set('smtp_sender', request.form.get('smtp_sender', ''))
        
        # Slack settings
        Settings.set('slack_webhook_url', request.form.get('slack_webhook_url', ''), encrypted=True)
        Settings.set('slack_enabled', request.form.get('slack_enabled', 'false'))
        
        # GitHub settings
        Settings.set('github_token', request.form.get('github_token', ''), encrypted=True)
        Settings.set('github_enabled', request.form.get('github_enabled', 'false'))
        
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('admin.settings'))
    
    # Load current settings
    current_settings = {
        'smtp_server': Settings.get('smtp_server', ''),
        'smtp_port': Settings.get('smtp_port', '587'),
        'smtp_username': Settings.get('smtp_username', ''),
        'smtp_use_tls': Settings.get('smtp_use_tls', 'true'),
        'smtp_sender': Settings.get('smtp_sender', ''),
        'slack_webhook_url': Settings.get('slack_webhook_url', ''),
        'slack_enabled': Settings.get('slack_enabled', 'false'),
        'github_token': Settings.get('github_token', ''),
        'github_enabled': Settings.get('github_enabled', 'false'),
    }
    
    return render_template('admin/settings.html', settings=current_settings)


@admin_bp.route('/projects')
@login_required
@admin_required
def projects():
    """Project management page."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Project.query
    
    if search:
        query = query.filter(
            (Project.name.ilike(f'%{search}%')) |
            (Project.key.ilike(f'%{search}%'))
        )
    
    projects = query.order_by(Project.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/projects.html',
                          projects=projects,
                          search=search)


@admin_bp.route('/export/issues')
@login_required
@admin_required
def export_issues():
    """Export issues to CSV."""
    issues = Issue.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Key', 'Title', 'Status', 'Priority', 'Type',
        'Reporter', 'Assignee', 'Project', 'Created', 'Updated', 'Due Date'
    ])
    
    # Data
    for issue in issues:
        writer.writerow([
            issue.key,
            issue.title,
            issue.status.value,
            issue.priority.value,
            issue.issue_type,
            issue.reporter.username if issue.reporter else '',
            issue.assignee.username if issue.assignee else '',
            issue.project.name,
            issue.created_at.strftime('%Y-%m-%d %H:%M'),
            issue.updated_at.strftime('%Y-%m-%d %H:%M'),
            issue.due_date.strftime('%Y-%m-%d') if issue.due_date else ''
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=issues_export_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }
    )


@admin_bp.route('/export/users')
@login_required
@admin_required
def export_users():
    """Export users to CSV."""
    users = User.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Username', 'Email', 'Full Name', 'Role',
        'Active', 'Verified', 'Created', 'Last Login'
    ])
    
    # Data
    for user in users:
        writer.writerow([
            user.username,
            user.email,
            user.full_name,
            user.role.value,
            'Yes' if user.is_active else 'No',
            'Yes' if user.is_verified else 'No',
            user.created_at.strftime('%Y-%m-%d %H:%M'),
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else ''
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=users_export_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }
    )


@admin_bp.route('/stats/api')
@login_required
@admin_required
def stats_api():
    """API endpoint for dashboard statistics."""
    # Issues by status
    status_data = []
    for status in IssueStatus:
        count = Issue.query.filter(Issue.status == status).count()
        status_data.append({'status': status.value, 'count': count})
    
    # Issues by priority
    priority_data = []
    for priority in IssuePriority:
        count = Issue.query.filter(Issue.priority == priority).count()
        priority_data.append({'priority': priority.value, 'count': count})
    
    return jsonify({
        'by_status': status_data,
        'by_priority': priority_data
    })


@admin_bp.route('/invitations')
@login_required
@admin_required
def invitations():
    """Manage user invitations."""
    from models import Invitation, Organization, organization_members
    
    # Get organizations the admin has access to
    if current_user.role == UserRole.ADMIN:
        organizations = Organization.query.all()
    else:
        # Get organizations where user is a member
        organizations = Organization.query.join(organization_members).filter(
            organization_members.c.user_id == current_user.id
        ).all()
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    
    # Base query
    query = Invitation.query
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Get invitations
    invitations_list = query.order_by(Invitation.created_at.desc()).all()
    
    # Get statistics
    total_invitations = Invitation.query.count()
    pending_invitations = Invitation.query.filter_by(status='pending').count()
    accepted_invitations = Invitation.query.filter_by(status='accepted').count()
    expired_invitations = Invitation.query.filter(
        Invitation.status == 'pending',
        Invitation.expires_at < datetime.utcnow()
    ).count()
    
    return render_template('admin/invitations.html',
                         invitations=invitations_list,
                         total_invitations=total_invitations,
                         pending_invitations=pending_invitations,
                         accepted_invitations=accepted_invitations,
                         expired_invitations=expired_invitations,
                         status_filter=status_filter,
                         organizations=organizations)


@admin_bp.route('/invitations/send', methods=['POST'])
@login_required
@admin_required
def send_invitation():
    """Send a new invitation."""
    from models import Invitation, Organization
    from services.email_service import send_invitation_email
    
    email = request.form.get('email', '').strip().lower()
    role_str = request.form.get('role', 'developer')
    organization_id = request.form.get('organization_id', type=int)
    
    # Validation
    if not email or '@' not in email:
        flash('Valid email address is required.', 'danger')
        return redirect(url_for('admin.invitations'))
    
    if not organization_id:
        flash('Organization is required.', 'danger')
        return redirect(url_for('admin.invitations'))
    
    # Verify organization exists and user has access
    organization = Organization.query.get(organization_id)
    if not organization:
        flash('Invalid organization.', 'danger')
        return redirect(url_for('admin.invitations'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash(f'A user with email {email} already exists.', 'warning')
        return redirect(url_for('admin.invitations'))
    
    # Check if there's already a pending invitation
    existing_invitation = Invitation.query.filter_by(
        email=email, 
        status='pending'
    ).first()
    
    if existing_invitation and not existing_invitation.is_expired():
        flash(f'An invitation has already been sent to {email}.', 'info')
        return redirect(url_for('admin.invitations'))
    
    # Cancel any expired invitations for this email
    if existing_invitation and existing_invitation.is_expired():
        existing_invitation.status = 'expired'
        db.session.commit()
    
    # Parse role
    try:
        role = UserRole[role_str.upper()]
    except KeyError:
        role = UserRole.DEVELOPER
    
    # Create invitation
    invitation = Invitation(
        email=email,
        role=role,
        invited_by_id=current_user.id,
        organization_id=organization_id
    )
    
    db.session.add(invitation)
    db.session.commit()
    
    # Send email
    try:
        send_invitation_email(invitation, current_user)
        flash(f'Invitation sent successfully to {email}!', 'success')
    except Exception as e:
        flash(f'Invitation created but email failed to send: {str(e)}', 'warning')
    
    return redirect(url_for('admin.invitations'))


@admin_bp.route('/invitations/<int:invitation_id>/resend', methods=['POST'])
@login_required
@admin_required
def resend_invitation(invitation_id):
    """Resend an invitation email."""
    from models import Invitation
    from services.email_service import send_invitation_email
    from datetime import timedelta
    
    invitation = Invitation.query.get_or_404(invitation_id)
    
    if invitation.status != 'pending':
        flash('Only pending invitations can be resent.', 'warning')
        return redirect(url_for('admin.invitations'))
    
    # Extend expiration if expired
    if invitation.is_expired():
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)
        db.session.commit()
    
    # Send email
    try:
        send_invitation_email(invitation, invitation.invited_by)
        flash(f'Invitation resent to {invitation.email}!', 'success')
    except Exception as e:
        flash(f'Failed to resend invitation: {str(e)}', 'danger')
    
    return redirect(url_for('admin.invitations'))


@admin_bp.route('/invitations/<int:invitation_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_invitation(invitation_id):
    """Cancel a pending invitation."""
    from models import Invitation
    
    invitation = Invitation.query.get_or_404(invitation_id)
    
    if invitation.status != 'pending':
        flash('Only pending invitations can be cancelled.', 'warning')
        return redirect(url_for('admin.invitations'))
    
    invitation.status = 'cancelled'
    db.session.commit()
    
    flash(f'Invitation to {invitation.email} has been cancelled.', 'success')
    return redirect(url_for('admin.invitations'))

