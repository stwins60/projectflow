"""
Database models for the Project Manager application.
Includes: User, Project, Issue, Comment, Attachment, Label, AuditLog
"""
from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from extensions import db, bcrypt
import secrets


class UserRole(Enum):
    """User roles enumeration."""
    ADMIN = 'admin'
    PROJECT_MANAGER = 'project_manager'
    DEVELOPER = 'developer'
    VIEWER = 'viewer'


class IssuePriority(Enum):
    """Issue priority levels."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class IssueStatus(Enum):
    """Issue status values."""
    BACKLOG = 'backlog'
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    CODE_REVIEW = 'code_review'
    DONE = 'done'


class IssueType(Enum):
    """Issue type enumeration."""
    BUG = 'bug'
    TASK = 'task'
    STORY = 'story'
    EPIC = 'epic'
    SUB_TASK = 'sub_task'
    FEATURE = 'feature'


class SubscriptionPlan(Enum):
    """Subscription plan types for multi-tenant SaaS."""
    FREE = 'free'
    STARTER = 'starter'
    PROFESSIONAL = 'professional'
    ENTERPRISE = 'enterprise'


class OrganizationStatus(Enum):
    """Organization status."""
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    TRIAL = 'trial'
    CANCELLED = 'cancelled'


# Association tables
organization_members = db.Table('organization_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organizations.id'), primary_key=True),
    db.Column('role', db.String(50), default='member'),  # 'owner', 'admin', 'member'
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

project_members = db.Table('project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

issue_labels = db.Table('issue_labels',
    db.Column('issue_id', db.Integer, db.ForeignKey('issues.id'), primary_key=True),
    db.Column('label_id', db.Integer, db.ForeignKey('labels.id'), primary_key=True)
)

issue_watchers = db.Table('issue_watchers',
    db.Column('issue_id', db.Integer, db.ForeignKey('issues.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

component_leads = db.Table('component_leads',
    db.Column('component_id', db.Integer, db.ForeignKey('components.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

issue_components = db.Table('issue_components',
    db.Column('issue_id', db.Integer, db.ForeignKey('issues.id'), primary_key=True),
    db.Column('component_id', db.Integer, db.ForeignKey('components.id'), primary_key=True)
)


class Organization(db.Model):
    """Organization model for multi-tenant SaaS."""
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    subdomain = db.Column(db.String(100), unique=True, nullable=True, index=True)
    
    # Subscription details
    plan = db.Column(db.Enum(SubscriptionPlan, native_enum=False), default=SubscriptionPlan.FREE, nullable=False)
    status = db.Column(db.Enum(OrganizationStatus, native_enum=False), default=OrganizationStatus.TRIAL, nullable=False)
    
    # Limits based on plan
    max_users = db.Column(db.Integer, default=5)
    max_projects = db.Column(db.Integer, default=3)
    max_storage_mb = db.Column(db.Integer, default=100)
    
    # Contact and billing
    contact_email = db.Column(db.String(120))
    billing_email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    
    # Address
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    
    # Customization
    logo_url = db.Column(db.String(255))
    primary_color = db.Column(db.String(7), default='#0d6efd')
    custom_domain = db.Column(db.String(255))
    
    # Settings
    settings = db.Column(db.JSON, default=dict)
    
    # Timestamps
    trial_ends_at = db.Column(db.DateTime)
    subscription_started_at = db.Column(db.DateTime)
    subscription_ends_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', secondary=organization_members, backref='organizations', lazy='dynamic')
    projects = db.relationship('Project', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Organization {self.name}>'
    
    @property
    def is_trial(self):
        """Check if organization is in trial period."""
        return self.status == OrganizationStatus.TRIAL
    
    @property
    def is_active(self):
        """Check if organization is active."""
        return self.status == OrganizationStatus.ACTIVE
    
    @property
    def trial_days_remaining(self):
        """Calculate remaining trial days."""
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def user_count(self):
        """Get current user count."""
        return self.users.count()
    
    @property
    def project_count(self):
        """Get current project count."""
        return self.projects.filter_by(is_active=True).count()
    
    def can_add_user(self):
        """Check if organization can add more users."""
        return self.user_count < self.max_users
    
    def can_add_project(self):
        """Check if organization can add more projects."""
        return self.project_count < self.max_projects
    
    def get_user_role(self, user):
        """Get user's role in organization."""
        result = db.session.execute(
            organization_members.select().where(
                organization_members.c.user_id == user.id,
                organization_members.c.organization_id == self.id
            )
        ).first()
        return result.role if result else None


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    avatar_url = db.Column(db.String(255))
    role = db.Column(db.Enum(UserRole), default=UserRole.DEVELOPER, nullable=False)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)
    
    # OAuth
    github_id = db.Column(db.String(50), unique=True, index=True)
    oauth_provider = db.Column(db.String(20))  # 'github', 'google', etc.
    github_access_token = db.Column(db.String(255))  # Store OAuth token for API access
    
    # Multi-tenancy fields
    current_organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    is_super_admin = db.Column(db.Boolean, default=False)  # Platform super admin
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    owned_projects = db.relationship('Project', backref='owner', lazy='dynamic',
                                     foreign_keys='Project.owner_id')
    assigned_issues = db.relationship('Issue', backref='assignee', lazy='dynamic',
                                      foreign_keys='Issue.assignee_id')
    created_issues = db.relationship('Issue', backref='reporter', lazy='dynamic',
                                     foreign_keys='Issue.reporter_id')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    projects = db.relationship('Project', secondary=project_members,
                               backref=db.backref('members', lazy='dynamic'))
    watched_issues = db.relationship('Issue', secondary=issue_watchers,
                                     backref=db.backref('watchers', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches the hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        """Generate a password reset token."""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify password reset token."""
        if self.reset_token == token and self.reset_token_expiry > datetime.utcnow():
            return True
        return False
    
    @property
    def full_name(self):
        """Return the user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    def can_manage_project(self, project):
        """Check if user can manage a project."""
        return (self.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER] and 
                (project.owner_id == self.id or self in project.members))
    
    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    """Project model for organizing issues."""
    __tablename__ = 'projects'
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'key', name='uq_org_project_key'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(10), nullable=False)  # e.g., "PROJ", "DEV"
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#6366f1')  # Hex color
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=False)
    
    # GitHub integration
    github_repo = db.Column(db.String(255))  # username/repo format
    github_enabled = db.Column(db.Boolean, default=False)
    
    # Slack integration
    slack_channel = db.Column(db.String(100))
    slack_enabled = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    issues = db.relationship('Issue', backref='project', lazy='dynamic',
                            cascade='all, delete-orphan')
    labels = db.relationship('Label', backref='project', lazy='dynamic',
                            cascade='all, delete-orphan')
    sprints = db.relationship('Sprint', backref='project', lazy='dynamic',
                             cascade='all, delete-orphan')
    components = db.relationship('Component', backref='project', lazy='dynamic',
                                cascade='all, delete-orphan')
    versions = db.relationship('Version', backref='project', lazy='dynamic',
                              cascade='all, delete-orphan')
    epics = db.relationship('Epic', backref='project', lazy='dynamic',
                           cascade='all, delete-orphan')
    
    @property
    def issue_count(self):
        """Get total number of issues."""
        return self.issues.count()
    
    @property
    def open_issues_count(self):
        """Get count of open issues."""
        return self.issues.filter(Issue.status != IssueStatus.DONE).count()
    
    def generate_issue_number(self):
        """Generate the next issue number for this project."""
        last_issue = self.issues.order_by(Issue.number.desc()).first()
        return (last_issue.number + 1) if last_issue else 1
    
    def __repr__(self):
        return f'<Project {self.key}: {self.name}>'


class Sprint(db.Model):
    """Sprint model for agile project management."""
    __tablename__ = 'sprints'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    goal = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=False)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    issues = db.relationship('Issue', backref='sprint', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def total_issues(self):
        """Get total number of issues in sprint."""
        return self.issues.count()
    
    @property
    def completed_issues(self):
        """Get number of completed issues."""
        return self.issues.filter(Issue.status == IssueStatus.DONE).count()
    
    @property
    def progress(self):
        """Calculate completion percentage."""
        total = self.total_issues
        if total == 0:
            return 0
        return int((self.completed_issues / total) * 100)
    
    @property
    def days_remaining(self):
        """Calculate days remaining in sprint."""
        if not self.end_date:
            return 0
        from datetime import date
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days
    
    @property
    def is_upcoming(self):
        """Check if sprint hasn't started yet."""
        if not self.start_date:
            return False
        from datetime import date
        return date.today() < self.start_date
    
    @property
    def is_completed(self):
        """Check if sprint is completed."""
        if not self.end_date:
            return False
        from datetime import date
        return date.today() > self.end_date and not self.is_active
    
    @property
    def status(self):
        """Get sprint status: active, upcoming, or completed."""
        if self.is_active:
            return 'active'
        elif self.is_upcoming:
            return 'upcoming'
        elif self.is_completed:
            return 'completed'
        else:
            return 'planned'
    
    def __repr__(self):
        return f'<Sprint {self.name}>'


class Epic(db.Model):
    """Epic model for grouping related issues into larger initiatives."""
    __tablename__ = 'epics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#8b5cf6')  # Purple by default
    
    # Epic status
    status = db.Column(db.String(20), default='open')  # open, in_progress, done, cancelled
    
    # Dates
    start_date = db.Column(db.Date)
    target_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner = db.relationship('User', backref='owned_epics')
    issues = db.relationship('Issue', backref='epic', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def progress(self):
        """Calculate completion percentage based on done issues."""
        total = self.issues.count()
        if total == 0:
            return 0
        done = self.issues.filter(Issue.status == IssueStatus.DONE).count()
        return int((done / total) * 100)
    
    @property
    def issue_count(self):
        """Get total issue count."""
        return self.issues.count()
    
    def __repr__(self):
        return f'<Epic {self.name}>'


class Component(db.Model):
    """Component model for organizing issues by system components."""
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lead = db.relationship('User', backref='led_components')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Component {self.name}>'


class Version(db.Model):
    """Version/Release model for tracking software releases."""
    __tablename__ = 'versions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "v1.0.0", "Sprint 1"
    description = db.Column(db.Text)
    
    # Release status
    status = db.Column(db.String(20), default='unreleased')  # unreleased, released, archived
    released = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)
    
    # Dates
    start_date = db.Column(db.Date)
    release_date = db.Column(db.Date)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    issues = db.relationship('Issue', backref='version', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def progress(self):
        """Calculate completion percentage."""
        total = self.issues.count()
        if total == 0:
            return 0
        done = self.issues.filter(Issue.status == IssueStatus.DONE).count()
        return int((done / total) * 100)
    
    def __repr__(self):
        return f'<Version {self.name}>'


class Issue(db.Model):
    """Issue model for tracking tasks, bugs, and features."""
    __tablename__ = 'issues'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)  # Project-specific number
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Status and priority
    status = db.Column(db.Enum(IssueStatus), default=IssueStatus.BACKLOG, nullable=False)
    priority = db.Column(db.Enum(IssuePriority), default=IssuePriority.MEDIUM, nullable=False)
    issue_type = db.Column(db.Enum(IssueType, name='issuetype', native_enum=True,
                                   values_callable=lambda x: [e.value for e in x]), 
                          default=IssueType.TASK, nullable=False)
    
    # Agile fields
    story_points = db.Column(db.Integer)  # Story point estimation
    
    # Requirements fields
    acceptance_criteria = db.Column(db.Text)  # For features/stories
    technical_requirements = db.Column(db.Text)  # Technical specs
    scope = db.Column(db.Text)  # Scope definition
    
    # Time tracking
    estimated_hours = db.Column(db.Float)
    logged_hours = db.Column(db.Float, default=0)
    due_date = db.Column(db.DateTime)
    
    # GitHub integration
    github_pr_url = db.Column(db.String(255))
    github_pr_status = db.Column(db.String(50))
    github_commit_sha = db.Column(db.String(40))
    github_branch = db.Column(db.String(255))  # Linked branch name
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprints.id'))
    epic_id = db.Column(db.Integer, db.ForeignKey('epics.id'))
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('issues.id'))  # For subtasks
    
    # Child relationships
    comments = db.relationship('Comment', backref='issue', lazy='dynamic',
                              cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='issue', lazy='dynamic',
                                 cascade='all, delete-orphan')
    labels = db.relationship('Label', secondary=issue_labels,
                            backref=db.backref('issues', lazy='dynamic'))
    components_list = db.relationship('Component', secondary=issue_components,
                                     backref=db.backref('issues', lazy='dynamic'))
    history = db.relationship('AuditLog', backref='issue', lazy='dynamic',
                             cascade='all, delete-orphan')
    subtasks = db.relationship('Issue', backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')
    
    @property
    def key(self):
        """Get the full issue key (e.g., PROJ-123)."""
        return f"{self.project.key}-{self.number}"
    
    @property
    def is_overdue(self):
        """Check if issue is overdue."""
        if self.due_date and self.status != IssueStatus.DONE:
            return datetime.utcnow() > self.due_date
        return False
    
    def __repr__(self):
        return f'<Issue {self.key}: {self.title}>'


class Comment(db.Model):
    """Comment model for issue discussions."""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<Comment {self.id} by {self.author.username}>'


class Attachment(db.Model):
    """Attachment model for issue files."""
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(100))
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader = db.relationship('User', backref='uploads')
    
    def __repr__(self):
        return f'<Attachment {self.original_filename}>'


class Label(db.Model):
    """Label model for categorizing issues."""
    __tablename__ = 'labels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6366f1')  # Hex color
    description = db.Column(db.String(200))
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    def __repr__(self):
        return f'<Label {self.name}>'


class AuditLog(db.Model):
    """Audit log model for tracking issue changes."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)  # created, updated, commented, etc.
    field_name = db.Column(db.String(50))  # Which field was changed
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} on issue {self.issue_id}>'


class Settings(db.Model):
    """Application settings model."""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    is_encrypted = db.Column(db.Boolean, default=False)
    
    # Timestamps
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get(key, default=None):
        """Get a setting value by key."""
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value, description=None, encrypted=False):
        """Set a setting value."""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value, description=description,
                             is_encrypted=encrypted)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<Settings {self.key}>'


class Invitation(db.Model):
    """User invitation model."""
    __tablename__ = 'invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.DEVELOPER, nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, accepted, expired, cancelled
    accepted_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_by = db.relationship('User', backref='sent_invitations')
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    organization = db.relationship('Organization', backref='invitations')
    
    def __init__(self, **kwargs):
        super(Invitation, self).__init__(**kwargs)
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            # Invitations expire in 7 days
            self.expires_at = datetime.utcnow() + timedelta(days=7)
    
    def is_expired(self):
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if invitation is valid and can be used."""
        return self.status == 'pending' and not self.is_expired()
    
    def __repr__(self):
        return f'<Invitation {self.email} - {self.status}>'


# Import timedelta for token expiry (needed in User model)
from datetime import timedelta


class WikiPage(db.Model):
    """Wiki page model for project documentation."""
    __tablename__ = 'wiki_pages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), nullable=False)
    content = db.Column(db.Text, nullable=True)
    
    # Project association
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    project = db.relationship('Project', backref=db.backref('wiki_pages', lazy='dynamic'))
    
    # Hierarchy support (parent-child pages)
    parent_id = db.Column(db.Integer, db.ForeignKey('wiki_pages.id'), nullable=True)
    parent = db.relationship('WikiPage', remote_side=[id], backref='children')
    
    # Author and timestamps
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ordering and visibility
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_wiki_pages')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_wiki_pages')
    
    def __repr__(self):
        return f'<WikiPage {self.title}>'
    
    @property
    def breadcrumbs(self):
        """Get breadcrumb trail for this page."""
        crumbs = [self]
        current = self.parent
        while current:
            crumbs.insert(0, current)
            current = current.parent
        return crumbs
    
    def get_all_descendants(self):
        """Get all descendant pages recursively."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants
