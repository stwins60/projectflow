"""
Organization routes for multi-tenant SaaS.
Handles organization signup, settings, and management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user, login_user
from sqlalchemy import or_
from extensions import db, bcrypt
from models import Organization, User, Project, SubscriptionPlan, OrganizationStatus, UserRole, organization_members
from datetime import datetime, timedelta
import re

org_bp = Blueprint('organization', __name__)


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


@org_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Organization signup page - create new workspace."""
    if request.method == 'POST':
        # Get form data
        org_name = request.form.get('org_name', '').strip()
        subdomain = request.form.get('subdomain', '').strip().lower()
        admin_name = request.form.get('admin_name', '').strip()
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_password = request.form.get('admin_password', '')
        
        # Validation
        errors = []
        
        if not org_name:
            errors.append('Organization name is required.')
        
        if not subdomain:
            errors.append('Subdomain is required.')
        elif not re.match(r'^[a-z0-9-]+$', subdomain):
            errors.append('Subdomain can only contain lowercase letters, numbers, and hyphens.')
        elif len(subdomain) < 3:
            errors.append('Subdomain must be at least 3 characters.')
        
        if not admin_email:
            errors.append('Admin email is required.')
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', admin_email):
            errors.append('Invalid email address.')
        
        if not admin_password or len(admin_password) < 6:
            errors.append('Password must be at least 6 characters.')
        
        # Check for existing subdomain
        if subdomain and Organization.query.filter_by(subdomain=subdomain).first():
            errors.append('Subdomain already taken. Please choose another.')
        
        # Check for existing email
        if admin_email and User.query.filter_by(email=admin_email).first():
            errors.append('Email already registered. Please login instead.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('organization/signup.html',
                                 org_name=org_name,
                                 subdomain=subdomain,
                                 admin_name=admin_name,
                                 admin_email=admin_email)
        
        # Create organization
        slug = slugify(org_name)
        
        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while Organization.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        organization = Organization(
            name=org_name,
            slug=slug,
            subdomain=subdomain,
            plan=SubscriptionPlan.FREE,
            status=OrganizationStatus.TRIAL,
            trial_ends_at=datetime.utcnow() + timedelta(days=14),  # 14-day trial
            max_users=5,
            max_projects=3,
            max_storage_mb=100
        )
        
        db.session.add(organization)
        db.session.flush()
        
        # Create admin user
        username = admin_email.split('@')[0]
        base_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=admin_email,
            username=username,
            password_hash=bcrypt.generate_password_hash(admin_password).decode('utf-8'),
            first_name=admin_name.split()[0] if admin_name else '',
            last_name=' '.join(admin_name.split()[1:]) if len(admin_name.split()) > 1 else '',
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            current_organization_id=organization.id
        )
        
        db.session.add(user)
        db.session.flush()
        
        # Add user to organization as owner
        stmt = organization_members.insert().values(
            user_id=user.id,
            organization_id=organization.id,
            role='owner'
        )
        db.session.execute(stmt)
        
        db.session.commit()
        
        # Login the user
        login_user(user)
        
        flash(f'Welcome to {org_name}! Your 14-day trial has started.', 'success')
        return redirect(url_for('dashboard.index'))
    
    # GET request
    return render_template('organization/signup.html')


@org_bp.route('/settings')
@login_required
def settings():
    """Organization settings page."""
    if not current_user.current_organization_id:
        flash('No organization selected.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    organization = Organization.query.get_or_404(current_user.current_organization_id)
    
    # Check if user is org admin or owner
    user_role = organization.get_user_role(current_user)
    if user_role not in ['owner', 'admin']:
        flash('You do not have permission to access organization settings.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    return render_template('organization/settings.html',
                         organization=organization,
                         user_role=user_role)


@org_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update organization settings."""
    if not current_user.current_organization_id:
        flash('No organization selected.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    organization = Organization.query.get_or_404(current_user.current_organization_id)
    
    # Check if user is org admin or owner
    user_role = organization.get_user_role(current_user)
    if user_role not in ['owner', 'admin']:
        flash('You do not have permission to update organization settings.', 'danger')
        return redirect(url_for('organization.settings'))
    
    # Update basic info
    organization.name = request.form.get('name', organization.name).strip()
    organization.contact_email = request.form.get('contact_email', '').strip() or None
    organization.phone = request.form.get('phone', '').strip() or None
    
    # Update address
    organization.address = request.form.get('address', '').strip() or None
    organization.city = request.form.get('city', '').strip() or None
    organization.state = request.form.get('state', '').strip() or None
    organization.country = request.form.get('country', '').strip() or None
    organization.postal_code = request.form.get('postal_code', '').strip() or None
    
    # Update customization
    primary_color = request.form.get('primary_color', '').strip()
    if primary_color and re.match(r'^#[0-9A-Fa-f]{6}$', primary_color):
        organization.primary_color = primary_color
    
    organization.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Organization settings updated successfully!', 'success')
    return redirect(url_for('organization.settings'))


@org_bp.route('/members')
@login_required
def members():
    """Organization members management."""
    if not current_user.current_organization_id:
        flash('No organization selected.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    organization = Organization.query.get_or_404(current_user.current_organization_id)
    
    # Get all members with their roles
    members_data = []
    for user in organization.users:
        role = organization.get_user_role(user)
        members_data.append({
            'user': user,
            'role': role
        })
    
    user_role = organization.get_user_role(current_user)
    
    return render_template('organization/members.html',
                         organization=organization,
                         members=members_data,
                         user_role=user_role)


@org_bp.route('/members/invite', methods=['POST'])
@login_required
def invite_member():
    """Invite a new member to organization."""
    if not current_user.current_organization_id:
        flash('No organization selected.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    organization = Organization.query.get_or_404(current_user.current_organization_id)
    
    # Check if user is org admin or owner
    user_role = organization.get_user_role(current_user)
    if user_role not in ['owner', 'admin']:
        flash('You do not have permission to invite members.', 'danger')
        return redirect(url_for('organization.members'))
    
    # Check user limit
    if not organization.can_add_user():
        flash(f'User limit reached ({organization.max_users}). Please upgrade your plan.', 'warning')
        return redirect(url_for('organization.members'))
    
    email = request.form.get('email', '').strip().lower()
    member_role = request.form.get('role', 'member')
    
    if not email:
        flash('Email is required.', 'danger')
        return redirect(url_for('organization.members'))
    
    # Check if user already exists
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Check if already in organization
        if user in organization.users:
            flash('User is already a member of this organization.', 'warning')
            return redirect(url_for('organization.members'))
        
        # Add existing user to organization
        stmt = organization_members.insert().values(
            user_id=user.id,
            organization_id=organization.id,
            role=member_role
        )
        db.session.execute(stmt)
        db.session.commit()
        
        flash(f'{email} added to organization!', 'success')
    else:
        # TODO: Send invitation email
        flash(f'Invitation sent to {email}. (Email functionality to be implemented)', 'info')
    
    return redirect(url_for('organization.members'))


@org_bp.route('/switch/<int:org_id>')
@login_required
def switch_organization(org_id):
    """Switch to a different organization."""
    organization = Organization.query.get_or_404(org_id)
    
    # Check if user is member of this organization
    if current_user not in organization.users:
        flash('You are not a member of this organization.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Update current organization
    current_user.current_organization_id = org_id
    db.session.commit()
    
    flash(f'Switched to {organization.name}', 'success')
    return redirect(url_for('dashboard.index'))


@org_bp.route('/billing')
@login_required
def billing():
    """Organization billing and subscription management."""
    if not current_user.current_organization_id:
        flash('No organization selected.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    organization = Organization.query.get_or_404(current_user.current_organization_id)
    
    # Check if user is org admin or owner
    user_role = organization.get_user_role(current_user)
    if user_role not in ['owner', 'admin']:
        flash('You do not have permission to access billing.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Define plan features
    plans = {
        'free': {
            'name': 'Free',
            'price': 0,
            'users': 5,
            'projects': 3,
            'storage': '100 MB',
            'features': ['Basic project management', 'Issue tracking', 'Wiki documentation']
        },
        'starter': {
            'name': 'Starter',
            'price': 29,
            'users': 10,
            'projects': 10,
            'storage': '1 GB',
            'features': ['Everything in Free', 'GitHub integration', 'Slack notifications', 'Custom branding']
        },
        'professional': {
            'name': 'Professional',
            'price': 79,
            'users': 50,
            'projects': 50,
            'storage': '10 GB',
            'features': ['Everything in Starter', 'Advanced reporting', 'API access', 'Priority support']
        },
        'enterprise': {
            'name': 'Enterprise',
            'price': 199,
            'users': 'Unlimited',
            'projects': 'Unlimited',
            'storage': '100 GB',
            'features': ['Everything in Professional', 'Custom domain', 'SSO', 'Dedicated support', 'SLA']
        }
    }
    
    return render_template('organization/billing.html',
                         organization=organization,
                         user_role=user_role,
                         plans=plans)
