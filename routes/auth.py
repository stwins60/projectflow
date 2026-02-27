"""
Authentication routes for user login, registration, password reset.
"""
import os
import secrets
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
import requests
from extensions import db, limiter
from models import User, UserRole
from services.email_service import send_verification_email, send_password_reset_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html')
            
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        
        flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        # Create user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.DEVELOPER
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        try:
            send_verification_email(user)
            flash('Registration successful! Please check your email to verify your account.', 'success')
        except Exception as e:
            # For development, auto-verify
            user.is_verified = True
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


@auth_bp.route('/verify/<token>')
def verify_email(token):
    """Verify user email address."""
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        flash('Invalid verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    if user.is_verified:
        flash('Email already verified.', 'info')
        return redirect(url_for('auth.login'))
    
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    
    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            
            try:
                send_password_reset_email(user, token)
            except Exception as e:
                pass  # Silently fail to not reveal user existence
        
        # Always show success to prevent email enumeration
        flash('If your email is registered, you will receive a password reset link.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# GitHub OAuth Routes
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_API = 'https://api.github.com/user'
GITHUB_EMAILS_API = 'https://api.github.com/user/emails'


@auth_bp.route('/github/login')
def github_login():
    """Initiate GitHub OAuth login."""
    if not current_app.config.get('GITHUB_OAUTH_ENABLED'):
        flash('GitHub login is not enabled.', 'warning')
        return redirect(url_for('auth.login'))
    
    client_id = current_app.config.get('GITHUB_CLIENT_ID')
    if not client_id:
        flash('GitHub OAuth is not configured.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Build authorization URL using APP_URL for correct external URL
    app_url = current_app.config.get('APP_URL', '').rstrip('/')
    redirect_uri = f"{app_url}/auth/github/callback"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'user:email read:user repo read:org',  # repo for issues/PRs, read:org for org repos
        'state': state
    }
    
    auth_url = f"{GITHUB_AUTHORIZE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return redirect(auth_url)


@auth_bp.route('/github/callback')
def github_callback():
    """Handle GitHub OAuth callback."""
    if not current_app.config.get('GITHUB_OAUTH_ENABLED'):
        flash('GitHub login is not enabled.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Verify state for CSRF protection
    state = request.args.get('state')
    if not state or state != session.pop('oauth_state', None):
        flash('Invalid OAuth state. Please try again.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check for errors
    error = request.args.get('error')
    if error:
        flash(f'GitHub login failed: {error}', 'danger')
        return redirect(url_for('auth.login'))
    
    # Exchange code for access token
    code = request.args.get('code')
    if not code:
        flash('No authorization code received.', 'danger')
        return redirect(url_for('auth.login'))
    
    client_id = current_app.config.get('GITHUB_CLIENT_ID')
    client_secret = current_app.config.get('GITHUB_CLIENT_SECRET')
    
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code
        },
        headers={'Accept': 'application/json'},
        timeout=10
    )
    
    if token_response.status_code != 200:
        flash('Failed to authenticate with GitHub.', 'danger')
        return redirect(url_for('auth.login'))
    
    token_data = token_response.json()
    access_token = token_data.get('access_token')
    
    if not access_token:
        flash('Failed to get access token from GitHub.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Get user info from GitHub
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    user_response = requests.get(GITHUB_USER_API, headers=headers, timeout=10)
    if user_response.status_code != 200:
        flash('Failed to get user info from GitHub.', 'danger')
        return redirect(url_for('auth.login'))
    
    github_user = user_response.json()
    github_id = str(github_user.get('id'))
    github_username = github_user.get('login')
    github_name = github_user.get('name') or github_username
    github_avatar = github_user.get('avatar_url')
    
    # Get primary email from GitHub
    email = github_user.get('email')
    if not email:
        emails_response = requests.get(GITHUB_EMAILS_API, headers=headers, timeout=10)
        if emails_response.status_code == 200:
            emails = emails_response.json()
            for email_obj in emails:
                if email_obj.get('primary') and email_obj.get('verified'):
                    email = email_obj.get('email')
                    break
    
    if not email:
        flash('Could not get email from GitHub. Please ensure your email is public or verified.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Find or create user
    user = User.query.filter_by(github_id=github_id).first()
    
    if not user:
        # Check if user exists with same email
        user = User.query.filter_by(email=email.lower()).first()
        if user:
            # Link GitHub account to existing user
            user.github_id = github_id
            user.oauth_provider = 'github'
            user.github_access_token = access_token
            if not user.avatar_url:
                user.avatar_url = github_avatar
        else:
            # Create new user
            # Generate unique username if needed
            base_username = github_username
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Split name into first and last
            name_parts = github_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Make the first user an ADMIN
            is_first_user = User.query.count() == 0
            
            user = User(
                email=email.lower(),
                username=username,
                first_name=first_name,
                last_name=last_name,
                avatar_url=github_avatar,
                github_id=github_id,
                oauth_provider='github',
                github_access_token=access_token,
                role=UserRole.ADMIN if is_first_user else UserRole.DEVELOPER,
                is_verified=True,  # GitHub email is verified
                is_active=True
            )
            # Set a random password (user can set one later if needed)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
    else:
        # Update token for existing GitHub user
        user.github_access_token = access_token
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Log in user
    login_user(user, remember=True)
    flash(f'Welcome, {user.first_name or user.username}!', 'success')
    
    next_page = request.args.get('next')
    return redirect(next_page or url_for('dashboard.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        
        # Change password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            current_password = request.form.get('current_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return render_template('auth/profile.html')
            
            if len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'danger')
                return render_template('auth/profile.html')
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return render_template('auth/profile.html')
            
            current_user.set_password(new_password)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    
    return render_template('auth/profile.html')


@auth_bp.route('/invite/<token>')
def accept_invitation(token):
    """Accept an invitation and proceed to registration."""
    from models import Invitation
    
    invitation = Invitation.query.filter_by(token=token).first()
    
    if not invitation:
        flash('Invalid invitation link.', 'danger')
        return redirect(url_for('auth.login'))
    
    if not invitation.is_valid():
        if invitation.is_expired():
            flash('This invitation has expired. Please contact your administrator for a new invitation.', 'warning')
        else:
            flash('This invitation is no longer valid.', 'info')
        return redirect(url_for('auth.login'))
    
    # Redirect to registration with invitation token
    return redirect(url_for('auth.register_with_invitation', token=token))


@auth_bp.route('/register/invited/<token>', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register_with_invitation(token):
    """Register using an invitation token."""
    from models import Invitation
    
    invitation = Invitation.query.filter_by(token=token).first()
    
    if not invitation or not invitation.is_valid():
        flash('Invalid or expired invitation.', 'danger')
        return redirect(url_for('auth.register'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        
        # Double-check email isn't already registered
        if User.query.filter_by(email=invitation.email).first():
            errors.append('This email is already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register_invited.html', invitation=invitation)
        
        # Create user with invitation details
        user = User(
            email=invitation.email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=invitation.role,
            is_verified=True,  # Auto-verify invited users
            current_organization_id=invitation.organization_id  # Set their current organization
        )
        user.set_password(password)
        
        # Mark invitation as accepted
        invitation.status = 'accepted'
        invitation.accepted_at = datetime.utcnow()
        
        db.session.add(user)
        db.session.flush()  # Flush to get user.id before adding to organization
        
        # Add user to the organization they were invited to
        from models import organization_members
        db.session.execute(
            organization_members.insert().values(
                user_id=user.id,
                organization_id=invitation.organization_id,
                role=invitation.role.value
            )
        )
        
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register_invited.html', invitation=invitation)

