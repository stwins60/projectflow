"""
Flask extensions initialization.
All extensions are initialized here to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database
db = SQLAlchemy()

# Database migrations
migrate = Migrate()

# Password hashing
bcrypt = Bcrypt()

# Login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Mail
mail = Mail()

# CSRF protection
csrf = CSRFProtect()

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
