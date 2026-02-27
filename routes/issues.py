"""
Issue management routes for creating, viewing, and managing issues.
"""
import os
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db, csrf
from models import (Issue, Project, Comment, Attachment, Label, AuditLog,
                    IssueStatus, IssuePriority, IssueType, User, Epic, 
                    Component, Version, Sprint)
from services.slack_service import send_slack_notification
from services.github_service import link_github_pr, is_github_enabled

issues_bp = Blueprint('issues', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def log_issue_change(issue, action, field_name=None, old_value=None, new_value=None):
    """Log an issue change to audit trail."""
    log = AuditLog(
        issue_id=issue.id,
        user_id=current_user.id,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value else None,
        new_value=str(new_value) if new_value else None
    )
    db.session.add(log)


@issues_bp.route('/')
@login_required
def index():
    """List all issues the user has access to."""
    if not current_user.current_organization_id:
        return redirect(url_for('organization.signup'))
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    project_id = request.args.get('project', None, type=int)
    search = request.args.get('search', '')
    
    # Base query with organization filtering
    query = Issue.query.join(Project).filter(
        Project.organization_id == current_user.current_organization_id
    )
    
    # Filter by project if specified
    if project_id:
        query = query.filter_by(project_id=project_id)
    
    # Filter by status
    if status != 'all':
        try:
            query = query.filter(Issue.status == IssueStatus(status))
        except ValueError:
            pass
    
    # Filter by priority
    if priority != 'all':
        try:
            query = query.filter(Issue.priority == IssuePriority(priority))
        except ValueError:
            pass
    
    # Search by title
    if search:
        query = query.filter(Issue.title.ilike(f'%{search}%'))
    
    # Order and paginate
    issues = query.order_by(Issue.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    # Get projects from current organization
    projects = Project.query.filter(
        Project.organization_id == current_user.current_organization_id,
        (Project.owner_id == current_user.id) | 
        (Project.members.any(id=current_user.id))
    ).all()
    
    return render_template('issues/index.html',
                          issues=issues,
                          projects=projects,
                          current_status=status,
                          current_priority=priority,
                          current_project=project_id,
                          search=search)


@issues_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new issue."""
    if not current_user.current_organization_id:
        flash('Please select an organization first.', 'warning')
        return redirect(url_for('organization.signup'))
    
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        acceptance_criteria = request.form.get('acceptance_criteria', '').strip()
        technical_requirements = request.form.get('technical_requirements', '').strip()
        scope = request.form.get('scope', '').strip()
        priority = request.form.get('priority', 'medium')
        issue_type = request.form.get('issue_type', 'task')
        story_points = request.form.get('story_points', type=int)
        assignee_id = request.form.get('assignee_id', type=int)
        epic_id = request.form.get('epic_id', type=int)
        sprint_id = request.form.get('sprint_id', type=int)
        version_id = request.form.get('version_id', type=int)
        parent_id = request.form.get('parent_id', type=int)
        due_date_str = request.form.get('due_date', '')
        label_ids = request.form.getlist('labels', type=int)
        component_ids = request.form.getlist('components', type=int)
        
        # Validation
        if not project_id:
            flash('Please select a project.', 'danger')
            return redirect(url_for('issues.create'))
        
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('issues.create'))
        
        # Verify project belongs to current organization
        project = Project.query.filter_by(
            id=project_id,
            organization_id=current_user.current_organization_id
        ).first_or_404()
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Create issue
        issue = Issue(
            project_id=project_id,
            number=project.generate_issue_number(),
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            technical_requirements=technical_requirements,
            scope=scope,
            priority=IssuePriority(priority),
            issue_type=IssueType(issue_type),
            story_points=story_points,
            reporter_id=current_user.id,
            assignee_id=assignee_id,
            epic_id=epic_id if epic_id else None,
            sprint_id=sprint_id if sprint_id else None,
            version_id=version_id if version_id else None,
            parent_id=parent_id if parent_id else None,
            due_date=due_date,
            status=IssueStatus.BACKLOG
        )
        
        # Add labels
        for label_id in label_ids:
            label = Label.query.get(label_id)
            if label and label.project_id == project_id:
                issue.labels.append(label)
        
        # Add components
        for component_id in component_ids:
            component = Component.query.get(component_id)
            if component and component.project_id == project_id:
                issue.components_list.append(component)
        
        db.session.add(issue)
        db.session.commit()
        
        # Log creation
        log_issue_change(issue, 'created')
        db.session.commit()
        
        # Send Slack notification
        send_slack_notification(
            'issue_created',
            issue=issue,
            user=current_user
        )
        
        flash(f'Issue {issue.key} created successfully!', 'success')
        return redirect(url_for('issues.view', issue_id=issue.id))
    
    # GET request - show form
    project_id = request.args.get('project_id', type=int)
    epic_id = request.args.get('epic_id', type=int)
    
    # Get projects from current organization
    projects = Project.query.filter(
        Project.organization_id == current_user.current_organization_id,
        (Project.owner_id == current_user.id) | 
        (Project.members.any(id=current_user.id))
    ).all()
    
    # Get users from current organization
    from models import organization_members
    users = User.query.join(organization_members).filter(
        organization_members.c.organization_id == current_user.current_organization_id,
        User.is_active == True
    ).all()
    
    # Get project-specific data if project is selected
    epics = []
    sprints = []
    versions = []
    components = []
    labels = []
    
    if project_id:
        project = Project.query.get(project_id)
        if project:
            epics = Epic.query.filter_by(project_id=project_id).all()
            sprints = Sprint.query.filter_by(project_id=project_id, is_active=True).all()
            versions = Version.query.filter_by(project_id=project_id, released=False).all()
            components = Component.query.filter_by(project_id=project_id).all()
            labels = Label.query.filter_by(project_id=project_id).all()
    
    return render_template('issues/create.html',
                          projects=projects,
                          users=users,
                          epics=epics,
                          sprints=sprints,
                          versions=versions,
                          components=components,
                          labels=labels,
                          priorities=IssuePriority,
                          issue_types=IssueType,
                          statuses=IssueStatus,
                          selected_project_id=project_id,
                          selected_epic_id=epic_id)


@issues_bp.route('/<int:issue_id>')
@login_required
def view(issue_id):
    """View issue details."""
    issue = Issue.query.get_or_404(issue_id)
    
    # Verify issue belongs to current organization
    if issue.project.organization_id != current_user.current_organization_id:
        flash('Issue not found.', 'danger')
        return redirect(url_for('issues.index'))
    
    comments = issue.comments.order_by(Comment.created_at.asc()).all()
    history = issue.history.order_by(AuditLog.created_at.desc()).limit(20).all()
    
    # Get users from current organization
    from models import organization_members
    users = User.query.join(organization_members).filter(
        organization_members.c.organization_id == current_user.current_organization_id,
        User.is_active == True
    ).all()
    
    # Get project-related data
    epics = Epic.query.filter_by(project_id=issue.project_id).all()
    sprints = Sprint.query.filter_by(project_id=issue.project_id).all()
    versions = Version.query.filter_by(project_id=issue.project_id, released=False).all()
    components = Component.query.filter_by(project_id=issue.project_id).all()
    labels = Label.query.filter_by(project_id=issue.project_id).all()
    
    # Get potential parent issues (for subtasks)
    potential_parents = Issue.query.filter(
        Issue.project_id == issue.project_id,
        Issue.id != issue.id,
        Issue.issue_type != IssueType.SUB_TASK
    ).all()
    
    return render_template('issues/view.html',
                          issue=issue,
                          comments=comments,
                          history=history,
                          users=users,
                          epics=epics,
                          sprints=sprints,
                          versions=versions,
                          components=components,
                          labels=labels,
                          potential_parents=potential_parents,
                          priorities=IssuePriority,
                          issue_types=IssueType,
                          statuses=IssueStatus,
                          github_enabled=is_github_enabled(),
                          user_has_github_token=bool(current_user.github_access_token))


@issues_bp.route('/<int:issue_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(issue_id):
    """Edit an issue."""
    issue = Issue.query.get_or_404(issue_id)
    
    # Verify issue belongs to current organization
    if issue.project.organization_id != current_user.current_organization_id:
        flash('Issue not found.', 'danger')
        return redirect(url_for('issues.index'))
    
    if request.method == 'POST':
        # Store old values for logging and notifications
        old_title = issue.title
        old_description = issue.description
        old_priority = issue.priority
        old_status = issue.status
        old_assignee_id = issue.assignee_id
        old_issue_type = issue.issue_type
        old_acceptance_criteria = issue.acceptance_criteria
        old_technical_requirements = issue.technical_requirements
        old_scope = issue.scope
        old_label_ids = set([label.id for label in issue.labels])
        old_due_date = issue.due_date
        old_estimated_hours = issue.estimated_hours
        
        # Track changes for notification
        changes = []
        
        # Update basic fields
        issue.title = request.form.get('title', '').strip()
        issue.description = request.form.get('description', '').strip()
        
        # Update new fields
        issue.acceptance_criteria = request.form.get('acceptance_criteria', '').strip()
        issue.technical_requirements = request.form.get('technical_requirements', '').strip()
        issue.scope = request.form.get('scope', '').strip()
        issue.issue_type = request.form.get('issue_type', 'task')
        
        # Update estimated hours
        estimated_hours_str = request.form.get('estimated_hours', '')
        if estimated_hours_str:
            try:
                issue.estimated_hours = float(estimated_hours_str)
            except ValueError:
                pass
        
        # Track estimated hours change
        if old_estimated_hours != issue.estimated_hours:
            old_hours_str = f"{old_estimated_hours}h" if old_estimated_hours else "None"
            new_hours_str = f"{issue.estimated_hours}h" if issue.estimated_hours else "None"
            changes.append({'field': 'estimated_hours', 'old': old_hours_str, 'new': new_hours_str})
        
        # Update priority
        new_priority = request.form.get('priority')
        if new_priority:
            issue.priority = IssuePriority(new_priority)
        
        # Update status
        new_status = request.form.get('status')
        if new_status:
            issue.status = IssueStatus(new_status)
            if issue.status == IssueStatus.DONE and not issue.resolved_at:
                issue.resolved_at = datetime.utcnow()
        
        # Update assignee
        new_assignee_id = request.form.get('assignee_id', type=int)
        issue.assignee_id = new_assignee_id
        
        # Update due date
        due_date_str = request.form.get('due_date', '')
        if due_date_str:
            try:
                issue.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        else:
            issue.due_date = None
        
        # Track due date change
        if old_due_date != issue.due_date:
            old_date_str = old_due_date.strftime('%Y-%m-%d') if old_due_date else 'None'
            new_date_str = issue.due_date.strftime('%Y-%m-%d') if issue.due_date else 'None'
            changes.append({'field': 'due_date', 'old': old_date_str, 'new': new_date_str})
        
        # Update labels
        label_ids = request.form.getlist('labels', type=int)
        new_label_ids = set(label_ids)
        
        # Track label changes
        added_label_ids = new_label_ids - old_label_ids
        removed_label_ids = old_label_ids - new_label_ids
        
        issue.labels.clear()
        for label_id in label_ids:
            label = Label.query.get(label_id)
            if label and label.project_id == issue.project_id:
                issue.labels.append(label)
        
        # Log changes and track for notifications
        has_changes = False
        
        if old_title != issue.title:
            log_issue_change(issue, 'updated', 'title', old_title, issue.title)
            changes.append({'field': 'title', 'old': old_title, 'new': issue.title})
            has_changes = True
            
        if old_description != issue.description:
            log_issue_change(issue, 'updated', 'description')
            changes.append({'field': 'description', 'old': 'Previous', 'new': 'Updated'})
            has_changes = True
            
        if old_acceptance_criteria != issue.acceptance_criteria:
            log_issue_change(issue, 'updated', 'acceptance_criteria')
            changes.append({'field': 'acceptance_criteria', 'old': 'Previous', 'new': 'Updated'})
            has_changes = True
            
        if old_technical_requirements != issue.technical_requirements:
            log_issue_change(issue, 'updated', 'technical_requirements')
            changes.append({'field': 'technical_requirements', 'old': 'Previous', 'new': 'Updated'})
            has_changes = True
            
        if old_scope != issue.scope:
            log_issue_change(issue, 'updated', 'scope')
            changes.append({'field': 'scope', 'old': 'Previous', 'new': 'Updated'})
            has_changes = True
            
        if old_issue_type != issue.issue_type:
            log_issue_change(issue, 'updated', 'issue_type', old_issue_type, issue.issue_type)
            changes.append({'field': 'issue_type', 'old': old_issue_type, 'new': issue.issue_type})
            has_changes = True
            
        if old_priority != issue.priority:
            log_issue_change(issue, 'updated', 'priority', old_priority.value, issue.priority.value)
            changes.append({'field': 'priority', 'old': old_priority.value.title(), 'new': issue.priority.value.title()})
            has_changes = True
            # Send priority change notification
            send_slack_notification('priority_changed', issue=issue, user=current_user,
                                   old_priority=old_priority.value, new_priority=issue.priority.value)
        
        if old_status != issue.status:
            log_issue_change(issue, 'updated', 'status', old_status.value, issue.status.value)
            changes.append({'field': 'status', 'old': old_status.value.replace('_', ' ').title(), 'new': issue.status.value.replace('_', ' ').title()})
            has_changes = True
            # Send Slack notification for status change
            send_slack_notification('status_updated', issue=issue, user=current_user,
                                   old_status=old_status.value, new_status=issue.status.value)
        
        if old_assignee_id != issue.assignee_id:
            old_assignee = User.query.get(old_assignee_id) if old_assignee_id else None
            new_assignee = User.query.get(issue.assignee_id) if issue.assignee_id else None
            log_issue_change(issue, 'updated', 'assignee',
                           old_assignee.username if old_assignee else None,
                           new_assignee.username if new_assignee else None)
            changes.append({'field': 'assignee', 
                          'old': old_assignee.username if old_assignee else 'Unassigned',
                          'new': new_assignee.username if new_assignee else 'Unassigned'})
            has_changes = True
            # Send Slack notification for assignment
            if new_assignee:
                send_slack_notification('issue_assigned', issue=issue, user=current_user,
                                       assignee=new_assignee)
        
        # Handle label changes
        if added_label_ids or removed_label_ids:
            added_labels = [Label.query.get(lid) for lid in added_label_ids]
            removed_labels = [Label.query.get(lid) for lid in removed_label_ids]
            
            if added_labels:
                changes.append({'field': 'labels_added', 'new': ', '.join([l.name for l in added_labels if l])})
            if removed_labels:
                changes.append({'field': 'labels_removed', 'old': ', '.join([l.name for l in removed_labels if l])})
            
            has_changes = True
            
            # Send label change notification
            send_slack_notification('labels_changed', issue=issue, user=current_user,
                                   added_labels=[l for l in added_labels if l],
                                   removed_labels=[l for l in removed_labels if l])
        
        # Send general update notification if there are changes not covered by specific notifications
        if has_changes:
            # Only send general update if it's not just status/assignee/priority/labels (already notified)
            other_changes = [c for c in changes if c['field'] not in ['status', 'assignee', 'priority', 'labels_added', 'labels_removed']]
            if other_changes:
                send_slack_notification('issue_updated', issue=issue, user=current_user, changes=other_changes)
        
        db.session.commit()
        flash('Issue updated successfully!', 'success')
        return redirect(url_for('issues.view', issue_id=issue.id))
    
    users = User.query.filter_by(is_active=True).all()
    labels = Label.query.filter_by(project_id=issue.project_id).all()
    
    return render_template('issues/edit.html',
                          issue=issue,
                          users=users,
                          labels=labels,
                          priorities=IssuePriority,
                          statuses=IssueStatus)


@issues_bp.route('/<int:issue_id>/reassign', methods=['POST'])
@login_required
def reassign(issue_id):
    """Quick reassign issue."""
    issue = Issue.query.get_or_404(issue_id)
    
    new_assignee_id = request.form.get('assignee_id', type=int)
    old_assignee_id = issue.assignee_id
    
    # Update assignee
    issue.assignee_id = new_assignee_id
    
    # Log the change
    old_assignee = User.query.get(old_assignee_id) if old_assignee_id else None
    new_assignee = User.query.get(new_assignee_id) if new_assignee_id else None
    log_issue_change(issue, 'updated', 'assignee',
                   old_assignee.username if old_assignee else None,
                   new_assignee.username if new_assignee else None)
    
    db.session.commit()
    
    # Send Slack notification
    if new_assignee:
        send_slack_notification('issue_assigned', issue=issue, user=current_user,
                               assignee=new_assignee)
    
    flash('Issue reassigned successfully!', 'success')
    return redirect(url_for('issues.view', issue_id=issue_id))


@issues_bp.route('/<int:issue_id>/comment', methods=['POST'])
@login_required
def add_comment(issue_id):
    """Add a comment to an issue."""
    issue = Issue.query.get_or_404(issue_id)
    content = request.form.get('content', '').strip()
    
    if not content:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('issues.view', issue_id=issue_id))
    
    comment = Comment(
        issue_id=issue_id,
        author_id=current_user.id,
        content=content
    )
    db.session.add(comment)
    
    log_issue_change(issue, 'commented')
    db.session.commit()
    
    # Send Slack notification
    send_slack_notification('comment_added', issue=issue, user=current_user, comment=comment)
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('issues.view', issue_id=issue_id))


@issues_bp.route('/<int:issue_id>/attachment', methods=['POST'])
@login_required
def add_attachment(issue_id):
    """Upload an attachment to an issue."""
    issue = Issue.query.get_or_404(issue_id)
    
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('issues.view', issue_id=issue_id))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('issues.view', issue_id=issue_id))
    
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        # Generate unique filename
        filename = f"{issue_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{original_filename}"
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        attachment = Attachment(
            issue_id=issue_id,
            uploader_id=current_user.id,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=file.content_type
        )
        db.session.add(attachment)
        
        log_issue_change(issue, 'attachment_added', 'attachment', None, original_filename)
        db.session.commit()
        
        flash('File uploaded successfully!', 'success')
    else:
        flash('File type not allowed.', 'danger')
    
    return redirect(url_for('issues.view', issue_id=issue_id))


@issues_bp.route('/<int:issue_id>/status', methods=['POST'])
@login_required
@csrf.exempt
def update_status(issue_id):
    """Quick update issue status (for Kanban board)."""
    issue = Issue.query.get_or_404(issue_id)
    new_status = request.json.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status required'}), 400
    
    try:
        old_status = issue.status
        issue.status = IssueStatus(new_status)
        
        if issue.status == IssueStatus.DONE and not issue.resolved_at:
            issue.resolved_at = datetime.utcnow()
        
        log_issue_change(issue, 'updated', 'status', old_status.value, issue.status.value)
        db.session.commit()
        
        # Send Slack notification
        send_slack_notification('status_updated', issue=issue, user=current_user,
                               old_status=old_status.value, new_status=issue.status.value)
        
        return jsonify({'success': True, 'status': issue.status.value})
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400


@issues_bp.route('/<int:issue_id>/github', methods=['POST'])
@login_required
def link_github(issue_id):
    """Link a GitHub PR or commit to an issue."""
    issue = Issue.query.get_or_404(issue_id)
    pr_url = request.form.get('pr_url', '').strip()
    commit_sha = request.form.get('commit_sha', '').strip()
    
    if pr_url:
        issue.github_pr_url = pr_url
        # Fetch PR status from GitHub
        pr_status = link_github_pr(issue.project.github_repo, pr_url)
        if pr_status:
            issue.github_pr_status = pr_status
        log_issue_change(issue, 'github_linked', 'pr_url', None, pr_url)
    
    if commit_sha:
        issue.github_commit_sha = commit_sha
        log_issue_change(issue, 'github_linked', 'commit_sha', None, commit_sha)
    
    db.session.commit()
    flash('GitHub link added successfully!', 'success')
    return redirect(url_for('issues.view', issue_id=issue_id))


@issues_bp.route('/kanban')
@issues_bp.route('/kanban/<int:project_id>')
@login_required
def kanban(project_id=None):
    """Kanban board view."""
    if not current_user.current_organization_id:
        return redirect(url_for('organization.signup'))
    
    if project_id:
        # Verify project belongs to current organization
        project = Project.query.filter_by(
            id=project_id,
            organization_id=current_user.current_organization_id
        ).first_or_404()
        issues = Issue.query.filter_by(project_id=project_id).all()
    else:
        project = None
        # Get issues from current organization only
        issues = Issue.query.join(Project).filter(
            Project.organization_id == current_user.current_organization_id,
            (Issue.assignee_id == current_user.id) | 
            (Issue.reporter_id == current_user.id)
        ).all()
    
    # Organize by status
    board = {
        IssueStatus.BACKLOG: [],
        IssueStatus.TODO: [],
        IssueStatus.IN_PROGRESS: [],
        IssueStatus.CODE_REVIEW: [],
        IssueStatus.DONE: []
    }
    
    for issue in issues:
        board[issue.status].append(issue)
    
    projects = Project.query.filter(
        (Project.owner_id == current_user.id) | 
        (Project.members.any(id=current_user.id))
    ).all()
    
    return render_template('issues/kanban.html',
                          board=board,
                          project=project,
                          projects=projects,
                          statuses=IssueStatus)


@issues_bp.route('/<int:issue_id>/delete', methods=['POST'])
@login_required
def delete(issue_id):
    """Delete an issue (admin or reporter only)."""
    issue = Issue.query.get_or_404(issue_id)
    
    if not (current_user.is_admin() or issue.reporter_id == current_user.id):
        flash('You do not have permission to delete this issue.', 'danger')
        return redirect(url_for('issues.view', issue_id=issue_id))
    
    project_id = issue.project_id
    db.session.delete(issue)
    db.session.commit()
    
    flash('Issue deleted successfully!', 'success')
    return redirect(url_for('projects.view', project_id=project_id))
