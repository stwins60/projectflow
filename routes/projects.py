"""
Project management routes.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import (Project, User, Label, Sprint, Issue, IssueStatus, UserRole,
                   Epic, Component, Version, IssueType)

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/')
@login_required
def index():
    """List all projects user has access to."""
    # Filter by current organization
    if not current_user.current_organization_id:
        flash('Please select an organization first.', 'warning')
        return redirect(url_for('organization.signup'))
    
    if current_user.is_admin():
        projects = Project.query.filter_by(organization_id=current_user.current_organization_id)\
            .order_by(Project.created_at.desc()).all()
    else:
        projects = Project.query.filter(
            Project.organization_id == current_user.current_organization_id,
            (Project.owner_id == current_user.id) |
            (Project.is_public == True) |
            (Project.members.any(id=current_user.id))
        ).order_by(Project.created_at.desc()).all()
    
    return render_template('projects/index.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new project."""
    if not current_user.current_organization_id:
        flash('Please select an organization first.', 'warning')
        return redirect(url_for('organization.signup'))
    
    if current_user.role not in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
        flash('You do not have permission to create projects.', 'danger')
        return redirect(url_for('projects.index'))
    
    # Get users from current organization only
    from models import organization_members
    users = User.query.join(organization_members).filter(
        organization_members.c.organization_id == current_user.current_organization_id,
        User.is_active == True
    ).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        key = request.form.get('key', '').strip().upper()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#6366f1')
        is_public = request.form.get('is_public') == 'on'
        github_repo = request.form.get('github_repo', '').strip()
        slack_channel = request.form.get('slack_channel', '').strip()
        
        # Validation
        if not name or not key:
            flash('Name and key are required.', 'danger')
            return render_template('projects/create.html', users=users)
        
        if len(key) > 10:
            flash('Project key must be 10 characters or less.', 'danger')
            return render_template('projects/create.html', users=users)
        
        if Project.query.filter_by(organization_id=current_user.current_organization_id, key=key).first():
            flash('Project key already exists in your organization.', 'danger')
            return render_template('projects/create.html', users=users)
        
        project = Project(
            name=name,
            key=key,
            description=description,
            color=color,
            is_public=is_public,
            owner_id=current_user.id,
            organization_id=current_user.current_organization_id,
            github_repo=github_repo,
            github_enabled=bool(github_repo),
            slack_channel=slack_channel,
            slack_enabled=bool(slack_channel)
        )
        
        # Add default labels
        default_labels = [
            ('Bug', '#ef4444', 'Something isn\'t working'),
            ('Feature', '#22c55e', 'New feature request'),
            ('Enhancement', '#3b82f6', 'Improvement to existing feature'),
            ('Documentation', '#a855f7', 'Documentation update'),
            ('Help Wanted', '#f59e0b', 'Extra attention is needed'),
        ]
        
        for label_name, label_color, label_desc in default_labels:
            label = Label(
                name=label_name,
                color=label_color,
                description=label_desc,
                project=project
            )
            db.session.add(label)
        
        db.session.add(project)
        db.session.commit()
        
        flash(f'Project {project.name} created successfully!', 'success')
        return redirect(url_for('projects.view', project_id=project.id))
    
    return render_template('projects/create.html', users=users)


@projects_bp.route('/<int:project_id>')
@login_required
def view(project_id):
    """View project details and issues."""
    project = Project.query.get_or_404(project_id)
    
    # Verify project belongs to current organization
    if project.organization_id != current_user.current_organization_id:
        flash('Project not found.', 'danger')
        return redirect(url_for('projects.index'))
    
    # Check access
    if not project.is_public and current_user not in project.members and \
       project.owner_id != current_user.id and not current_user.is_admin():
        flash('You do not have access to this project.', 'danger')
        return redirect(url_for('projects.index'))
    
    # Get issues grouped by status
    issues_by_status = {}
    for status in IssueStatus:
        issues_by_status[status] = project.issues.filter_by(status=status)\
            .order_by(Issue.priority.desc()).all()
    
    # Recent activity
    recent_issues = project.issues.order_by(Issue.updated_at.desc()).limit(10).all()
    
    return render_template('projects/view.html',
                          project=project,
                          issues_by_status=issues_by_status,
                          recent_issues=recent_issues,
                          statuses=IssueStatus)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_id):
    """Edit project settings."""
    project = Project.query.get_or_404(project_id)
    
    # Verify project belongs to current organization
    if project.organization_id != current_user.current_organization_id:
        flash('Project not found.', 'danger')
        return redirect(url_for('projects.index'))
    
    # Check permission
    if not current_user.can_manage_project(project):
        flash('You do not have permission to edit this project.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    if request.method == 'POST':
        project.name = request.form.get('name', '').strip()
        project.description = request.form.get('description', '').strip()
        project.color = request.form.get('color', '#6366f1')
        project.is_public = request.form.get('is_public') == 'on'
        project.is_active = request.form.get('is_active') == 'on'
        project.github_repo = request.form.get('github_repo', '').strip()
        project.github_enabled = request.form.get('github_enabled') == 'on'
        project.slack_channel = request.form.get('slack_channel', '').strip()
        project.slack_enabled = request.form.get('slack_enabled') == 'on'
        
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects.view', project_id=project_id))
    
    return render_template('projects/edit.html', project=project)


@projects_bp.route('/<int:project_id>/members', methods=['GET', 'POST'])
@login_required
def members(project_id):
    """Manage project members."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage members.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    all_users = User.query.filter_by(is_active=True).all()
    current_members = list(project.members)
    available_users = [u for u in all_users if u not in current_members and u.id != project.owner_id]
    
    # Include owner in members list
    members_list = [project.owner] if project.owner else []
    members_list.extend([m for m in current_members if m.id != project.owner_id])
    
    return render_template('projects/members.html',
                          project=project,
                          members=members_list,
                          available_users=available_users)


@projects_bp.route('/<int:project_id>/members/add', methods=['POST'])
@login_required
def add_member(project_id):
    """Add a member to the project."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage members.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    user_id = request.form.get('user_id', type=int)
    if user_id:
        user = User.query.get(user_id)
        if user and user not in project.members:
            project.members.append(user)
            db.session.commit()
            flash(f'{user.username} added to project.', 'success')
    
    return redirect(url_for('projects.members', project_id=project_id))


@projects_bp.route('/<int:project_id>/members/remove', methods=['POST'])
@login_required
def remove_member(project_id):
    """Remove a member from the project."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage members.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    user_id = request.form.get('user_id', type=int)
    if user_id:
        user = User.query.get(user_id)
        if user and user in project.members and user.id != project.owner_id:
            project.members.remove(user)
            db.session.commit()
            flash(f'{user.username} removed from project.', 'success')
    
    return redirect(url_for('projects.members', project_id=project_id))


@projects_bp.route('/<int:project_id>/members/set-lead', methods=['POST'])
@login_required
def set_lead(project_id):
    """Set a member as project lead."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage project settings.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    user_id = request.form.get('user_id', type=int)
    if user_id:
        user = User.query.get(user_id)
        if user:
            project.lead_id = user_id
            db.session.commit()
            flash(f'{user.username} is now the project lead.', 'success')
    
    return redirect(url_for('projects.members', project_id=project_id))


@projects_bp.route('/<int:project_id>/labels', methods=['GET', 'POST'])
@login_required
def labels(project_id):
    """Manage project labels."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage labels.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            color = request.form.get('color', '#6366f1')
            description = request.form.get('description', '').strip()
            
            if name:
                label = Label(
                    name=name,
                    color=color,
                    description=description,
                    project_id=project_id
                )
                db.session.add(label)
                db.session.commit()
                flash('Label created successfully!', 'success')
        
        elif action == 'update':
            label_id = request.form.get('label_id', type=int)
            label = Label.query.get(label_id)
            if label and label.project_id == project_id:
                label.name = request.form.get('name', '').strip() or label.name
                label.color = request.form.get('color', label.color)
                label.description = request.form.get('description', '').strip()
                db.session.commit()
                flash('Label updated successfully!', 'success')
        
        elif action == 'delete':
            label_id = request.form.get('label_id', type=int)
            label = Label.query.get(label_id)
            if label and label.project_id == project_id:
                db.session.delete(label)
                db.session.commit()
                flash('Label deleted successfully!', 'success')
        
        return redirect(url_for('projects.labels', project_id=project_id))
    
    return render_template('projects/labels.html', project=project, labels=project.labels)


@projects_bp.route('/<int:project_id>/sprints', methods=['GET', 'POST'])
@login_required
def sprints(project_id):
    """Manage project sprints."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to manage sprints.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            from datetime import datetime
            
            name = request.form.get('name', '').strip()
            goal = request.form.get('goal', '').strip()
            start_date_str = request.form.get('start_date', '')
            end_date_str = request.form.get('end_date', '')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            
            if name:
                sprint = Sprint(
                    name=name,
                    goal=goal,
                    start_date=start_date,
                    end_date=end_date,
                    project_id=project_id
                )
                db.session.add(sprint)
                db.session.commit()
                flash('Sprint created successfully!', 'success')
        
        elif action == 'start':
            sprint_id = request.form.get('sprint_id', type=int)
            sprint = Sprint.query.get(sprint_id)
            if sprint and sprint.project_id == project_id:
                # Deactivate other sprints
                for s in project.sprints:
                    s.is_active = False
                sprint.is_active = True
                db.session.commit()
                flash(f'Sprint "{sprint.name}" started!', 'success')
        
        elif action == 'end':
            sprint_id = request.form.get('sprint_id', type=int)
            sprint = Sprint.query.get(sprint_id)
            if sprint and sprint.project_id == project_id:
                sprint.is_active = False
                db.session.commit()
                flash(f'Sprint "{sprint.name}" ended!', 'success')
        
        elif action == 'update':
            from datetime import datetime
            
            sprint_id = request.form.get('sprint_id', type=int)
            sprint = Sprint.query.get(sprint_id)
            
            if sprint and sprint.project_id == project_id:
                sprint.name = request.form.get('name', '').strip() or sprint.name
                sprint.goal = request.form.get('goal', '').strip()
                
                start_date_str = request.form.get('start_date', '')
                end_date_str = request.form.get('end_date', '')
                
                if start_date_str:
                    sprint.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                if end_date_str:
                    sprint.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                
                db.session.commit()
                flash(f'Sprint "{sprint.name}" updated successfully!', 'success')
        
        return redirect(url_for('projects.sprints', project_id=project_id))
    
    # Get all sprints for the project
    sprints = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.start_date).all()
    
    return render_template('projects/sprints.html', project=project, sprints=sprints)


@projects_bp.route('/<int:project_id>/archive', methods=['POST'])
@login_required
def archive(project_id):
    """Archive a project (admin or owner only)."""
    project = Project.query.get_or_404(project_id)
    
    if not (current_user.is_admin() or project.owner_id == current_user.id):
        flash('You do not have permission to archive this project.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    # Toggle archive status
    project.is_active = not project.is_active
    db.session.commit()
    
    status = 'unarchived' if project.is_active else 'archived'
    flash(f'Project {status} successfully!', 'success')
    return redirect(url_for('projects.index'))


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    """Delete a project (admin or owner only)."""
    project = Project.query.get_or_404(project_id)
    
    if not (current_user.is_admin() or project.owner_id == current_user.id):
        flash('You do not have permission to delete this project.', 'danger')
        return redirect(url_for('projects.view', project_id=project_id))
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects.index'))


# ============================================================================
# EPIC ROUTES
# ============================================================================

@projects_bp.route('/<int:project_id>/epics', methods=['GET'])
@login_required
def epics(project_id):
    """View and manage project epics."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project) and project not in current_user.projects:
        flash('You do not have access to this project.', 'danger')
        return redirect(url_for('projects.index'))
    
    epics = Epic.query.filter_by(project_id=project_id).order_by(Epic.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).all()
    
    return render_template('projects/epics.html', project=project, epics=epics, users=users)


@projects_bp.route('/<int:project_id>/epics/create', methods=['POST'])
@login_required
def create_epic(project_id):
    """Create a new epic."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to create epics.', 'danger')
        return redirect(url_for('projects.epics', project_id=project_id))
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#8b5cf6')
    owner_id = request.form.get('owner_id', type=int)
    
    if not name:
        flash('Epic name is required.', 'danger')
        return redirect(url_for('projects.epics', project_id=project_id))
    
    epic = Epic(
        name=name,
        description=description,
        color=color,
        project_id=project_id,
        owner_id=owner_id,
        status='open'
    )
    
    db.session.add(epic)
    db.session.commit()
    
    flash(f'Epic "{name}" created successfully!', 'success')
    return redirect(url_for('projects.epics', project_id=project_id))


@projects_bp.route('/<int:project_id>/epics/<int:epic_id>/edit', methods=['POST'])
@login_required
def edit_epic(project_id, epic_id):
    """Edit an epic."""
    project = Project.query.get_or_404(project_id)
    epic = Epic.query.get_or_404(epic_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to edit epics.', 'danger')
        return redirect(url_for('projects.epics', project_id=project_id))
    
    epic.name = request.form.get('name', epic.name).strip()
    epic.description = request.form.get('description', '').strip()
    epic.color = request.form.get('color', epic.color)
    epic.status = request.form.get('status', epic.status)
    epic.owner_id = request.form.get('owner_id', type=int)
    
    db.session.commit()
    flash(f'Epic "{epic.name}" updated successfully!', 'success')
    return redirect(url_for('projects.epics', project_id=project_id))


@projects_bp.route('/<int:project_id>/epics/<int:epic_id>/delete', methods=['POST'])
@login_required
def delete_epic(project_id, epic_id):
    """Delete an epic."""
    project = Project.query.get_or_404(project_id)
    epic = Epic.query.get_or_404(epic_id)
    
    if not current_user.can_manage_project(project):
        flash('You do not have permission to delete epics.', 'danger')
        return redirect(url_for('projects.epics', project_id=project_id))
    
    # Remove epic from all issues
    Issue.query.filter_by(epic_id=epic_id).update({'epic_id': None})
    
    db.session.delete(epic)
    db.session.commit()
    
    flash('Epic deleted successfully!', 'success')
    return redirect(url_for('projects.epics', project_id=project_id))


# ============================================================================
# COMPONENT ROUTES
# ============================================================================

@projects_bp.route('/<int:project_id>/components', methods=['GET', 'POST'])
@login_required
def components(project_id):
    """View and manage project components."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project) and project not in current_user.projects:
        flash('You do not have access to this project.', 'danger')
        return redirect(url_for('projects.index'))
    
    if request.method == 'POST':
        if not current_user.can_manage_project(project):
            flash('You do not have permission to manage components.', 'danger')
            return redirect(url_for('projects.components', project_id=project_id))
        
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            lead_id = request.form.get('lead_id', type=int)
            
            if not name:
                flash('Component name is required.', 'danger')
            else:
                component = Component(
                    name=name,
                    description=description,
                    project_id=project_id,
                    lead_id=lead_id
                )
                db.session.add(component)
                db.session.commit()
                flash(f'Component "{name}" created successfully!', 'success')
        
        elif action == 'delete':
            component_id = request.form.get('component_id', type=int)
            component = Component.query.get_or_404(component_id)
            db.session.delete(component)
            db.session.commit()
            flash('Component deleted successfully!', 'success')
        
        return redirect(url_for('projects.components', project_id=project_id))
    
    components = Component.query.filter_by(project_id=project_id).order_by(Component.name).all()
    users = User.query.filter_by(is_active=True).all()
    
    return render_template('projects/components.html', project=project, 
                          components=components, users=users)


# ============================================================================
# VERSION/RELEASE ROUTES
# ============================================================================

@projects_bp.route('/<int:project_id>/versions', methods=['GET', 'POST'])
@login_required
def versions(project_id):
    """View and manage project versions/releases."""
    project = Project.query.get_or_404(project_id)
    
    if not current_user.can_manage_project(project) and project not in current_user.projects:
        flash('You do not have access to this project.', 'danger')
        return redirect(url_for('projects.index'))
    
    if request.method == 'POST':
        if not current_user.can_manage_project(project):
            flash('You do not have permission to manage versions.', 'danger')
            return redirect(url_for('projects.versions', project_id=project_id))
        
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Version name is required.', 'danger')
            else:
                version = Version(
                    name=name,
                    description=description,
                    project_id=project_id,
                    status='unreleased'
                )
                db.session.add(version)
                db.session.commit()
                flash(f'Version "{name}" created successfully!', 'success')
        
        elif action == 'release':
            version_id = request.form.get('version_id', type=int)
            version = Version.query.get_or_404(version_id)
            version.released = True
            version.status = 'released'
            from datetime import datetime
            version.release_date = datetime.utcnow().date()
            db.session.commit()
            flash(f'Version "{version.name}" released!', 'success')
        
        elif action == 'delete':
            version_id = request.form.get('version_id', type=int)
            version = Version.query.get_or_404(version_id)
            db.session.delete(version)
            db.session.commit()
            flash('Version deleted successfully!', 'success')
        
        return redirect(url_for('projects.versions', project_id=project_id))
    
    versions = Version.query.filter_by(project_id=project_id).order_by(
        Version.released.asc(), Version.created_at.desc()).all()
    
    return render_template('projects/versions.html', project=project, versions=versions)

