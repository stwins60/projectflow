"""
Project Manager Application - Main Entry Point
A full-featured project management application similar to Jira.
"""
import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config
from extensions import db, migrate, bcrypt, login_manager, mail, csrf, limiter
from models import User, UserRole


def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configure proxy support for proper HTTPS detection behind reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.issues import issues_bp
    from routes.admin import admin_bp
    from routes.projects import projects_bp
    from routes.api import api_bp
    from routes.wiki import wiki_bp
    from routes.organization import org_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(issues_bp, url_prefix='/issues')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(wiki_bp)
    app.register_blueprint(org_bp, url_prefix='/org')
    
    # Multi-tenancy context processor
    @app.context_processor
    def inject_organization():
        """Inject current organization into all templates."""
        from models import Organization
        organization = None
        if current_user.is_authenticated and current_user.current_organization_id:
            organization = Organization.query.get(current_user.current_organization_id)
        return dict(current_organization=organization)
    
    # Before request handler for organization context
    @app.before_request
    def check_organization_status():
        """Check organization status and trial expiration."""
        from models import Organization, OrganizationStatus
        
        # Skip for public routes
        public_routes = ['auth.login', 'auth.register', 'organization.signup', 'static', 'health']
        if request.endpoint and any(request.endpoint.startswith(route) for route in public_routes):
            return
        
        if current_user.is_authenticated and current_user.current_organization_id:
            organization = Organization.query.get(current_user.current_organization_id)
            if organization:
                # Check if organization is suspended
                if organization.status == OrganizationStatus.SUSPENDED:
                    if request.endpoint != 'organization.billing':
                        flash('Your organization has been suspended. Please contact support.', 'danger')
                        return redirect(url_for('dashboard.index'))
    
    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('landing.html')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    # Context processors
    @app.context_processor
    def inject_globals():
        notifications = []
        if hasattr(current_user, 'id') and current_user.is_authenticated:
            from datetime import datetime, timedelta
            from models import Issue, IssueStatus, Comment
            
            # Get recent comments on user's issues
            recent_comments = Comment.query.join(Issue).filter(
                (Issue.assignee_id == current_user.id) | (Issue.reporter_id == current_user.id),
                Comment.author_id != current_user.id,
                Comment.created_at >= datetime.utcnow() - timedelta(days=7)
            ).order_by(Comment.created_at.desc()).limit(5).all()
            
            for comment in recent_comments:
                time_diff = datetime.utcnow() - comment.created_at
                if time_diff.days > 0:
                    time_ago = f"{time_diff.days}d ago"
                elif time_diff.seconds >= 3600:
                    time_ago = f"{time_diff.seconds // 3600}h ago"
                else:
                    time_ago = f"{time_diff.seconds // 60}m ago"
                
                notifications.append({
                    'message': f"New comment on {comment.issue.key}",
                    'url': f"/issues/{comment.issue.id}",
                    'icon': 'chat-left-text',
                    'time_ago': time_ago,
                    'read': False
                })
        
        return {
            'app_name': app.config.get('APP_NAME', 'ProjectFlow'),
            'current_year': 2026,
            'UserRole': UserRole,
            'notifications': notifications
        }
    
    # CLI commands
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database with default data."""
        db.create_all()
        
        # Create default admin user if not exists
        admin = User.query.filter_by(email='admin@projectflow.com').first()
        if not admin:
            admin = User(
                email='admin@projectflow.com',
                username='admin',
                first_name='Admin',
                last_name='User',
                role=UserRole.ADMIN,
                is_verified=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Default admin user created: admin@projectflow.com / admin123')
        
        print('Database initialized successfully!')
    
    @app.cli.command('create-admin')
    def create_admin():
        """Create an admin user."""
        import click
        email = click.prompt('Email')
        username = click.prompt('Username')
        password = click.prompt('Password', hide_input=True)
        
        user = User(
            email=email,
            username=username,
            role=UserRole.ADMIN,
            is_verified=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f'Admin user {username} created successfully!')
    
    @app.cli.command('promote-user')
    def promote_user():
        """Promote an existing user to admin."""
        import click
        identifier = click.prompt('Username or Email')
        
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()
        
        if not user:
            print(f'User "{identifier}" not found.')
            return
        
        user.role = UserRole.ADMIN
        db.session.commit()
        print(f'User {user.username} ({user.email}) promoted to ADMIN!')
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
