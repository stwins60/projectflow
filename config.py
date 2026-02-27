"""
Configuration settings for the Project Manager application.
Supports multiple environments: development, testing, production.
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class with common settings."""
    
    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    APP_NAME = os.environ.get('APP_NAME') or 'ProjectFlow'
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_ACCESS_TOKEN_HOURS', 24)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_DAYS', 30)))
    
    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@projectflow.com'
    
    # Security settings
    BCRYPT_LOG_ROUNDS = 12
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}
    
    # Slack integration
    SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
    SLACK_ENABLED = os.environ.get('SLACK_ENABLED', 'false').lower() == 'true'
    
    # GitHub integration
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_ENABLED = os.environ.get('GITHUB_ENABLED', 'false').lower() == 'true'
    
    # GitHub OAuth
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
    GITHUB_OAUTH_ENABLED = os.environ.get('GITHUB_OAUTH_ENABLED', 'false').lower() == 'true'
    
    # Application URL (for OAuth callbacks, emails, etc.)
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # Pagination
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'dev.db')
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Production-specific security settings
    # Note: Behind Cloudflare Tunnel/proxy, secure cookies work via X-Forwarded-Proto header
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CSRF settings for proxied environments (Cloudflare Tunnel, nginx, etc.)
    WTF_CSRF_SSL_STRICT = False  # Allow CSRF in proxied HTTPS environments
    WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        # Log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
