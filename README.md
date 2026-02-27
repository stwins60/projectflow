# Project Manager

A full-featured **Multi-Tenant** Project Management Web Application similar to Jira, built with Flask, Bootstrap 5, and PostgreSQL.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

<img src="static/img/logo.svg" alt="Project Manager" width="300">

## 📸 Screenshots

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/landing.png" alt="Landing Page" width="100%">
      <br/>
      <b>🏠 Landing Page</b> — Clean hero with features overview and quick signup
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/dashboard.png" alt="Dashboard" width="100%">
      <br/>
      <b>� Dashboard</b> — At-a-glance stats, weekly progress chart, and task distribution
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/kanban.png" alt="Kanban Board" width="100%">
      <br/>
      <b>�️ Kanban Board</b> — Drag-and-drop issue management across status columns
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/issues.png" alt="Issues List" width="100%">
      <br/>
      <b>� Issues</b> — Filterable issue list with search, status, priority, and project filters
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/projects.png" alt="Projects" width="100%">
      <br/>
      <b>📁 Projects</b> — Project management with a New Project button and full list view
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/org_signup.png" alt="Workspace Signup" width="100%">
      <br/>
      <b>🏢 Workspace Signup</b> — Simple org onboarding, free forever, no credit card needed
    </td>
  </tr>
</table>

## ✨ Features

### 🏢 Multi-Tenancy (SaaS)
- **Self-Hosted & Free**: Deploy on your own infrastructure at no cost
- **Organization Workspaces**: Each organization has isolated data and projects
- **Subdomain Support**: Custom subdomains for each organization (e.g., acme.projectmanager.app)
- **Secure Isolation**: Complete data separation between organizations

### Core Features
- **Issue Tracking**: Create, edit, and manage issues with priorities, statuses, and assignments
- **Kanban Board**: Drag-and-drop interface for visual issue management
- **Projects**: Organize work into projects with unique keys (e.g., PROJ-123)
- **Sprints**: Plan and track development cycles with sprint management
- **Epics & Components**: Organize large features and system components
- **Versions/Releases**: Track issue assignments to product versions
- **Labels**: Custom labels with colors for issue categorization
- **Comments & Attachments**: Collaborate with team comments and file attachments
- **Wiki Documentation**: Markdown-based wiki pages per project

### User Management
- **Organization Members**: Invite users to your organization workspace
- **Role-Based Access Control**: Admin, Project Manager, Developer, Viewer roles
- **JWT Authentication**: Secure login with password hashing
- **User Profiles**: Customizable user profiles with avatars
- **Activity Feed**: Track all user actions and changes
- **Email Invitations**: Invite team members via email

### Integrations
- **Slack Notifications**: Real-time notifications for issue updates (auto-route by issue type)
- **GitHub Integration**: Link issues to PRs and commits, OAuth login
- **AWS Bedrock AI**: AI-powered features (optional)
- **SMTP Email**: Email notifications and password reset

### Admin Dashboard
- **Analytics**: Charts showing issue trends and team performance
- **User Management**: Create, edit, and manage user accounts
- **Organization Settings**: Manage subscription, limits, and billing
- **System Settings**: Configure integrations and app settings
- **Export Data**: CSV export for reporting

### UI/UX
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Clean Bootstrap 5 interface with gradient themes
- **Custom Branding**: Configurable logo, colors, and app name per organization
- **Rich Text Editor**: Markdown support for descriptions and wiki pages

## 📋 Requirements

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: (optional, for rate limiting)
- **Docker & Docker Compose**: (recommended for deployment)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/stwins60/projectflow.git
cd projectflow
```

2. **Create environment file:**
```bash
# Copy the example environment file
cat > .env << EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Database Configuration
DB_USER=projectmgr
DB_PASSWORD=$(openssl rand -hex 16)
DB_NAME=projectmanager

# Application Settings
APP_NAME=ProjectFlow
APP_URL=http://localhost:5987

# Email Configuration (Optional - for notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@projectflow.com

# Slack Integration (Optional)
SLACK_WEBHOOK_URL=
SLACK_ENABLED=false

# GitHub Integration (Optional)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_OAUTH_ENABLED=false

# AWS Bedrock AI (Optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
EOF
```

3. **Start the application:**
```bash
docker compose up -d
```

4. **Wait for services to be healthy:**
```bash
docker compose ps
```

5. **Access the application:**
   - Open your browser to `http://localhost:5987`
   - Click "Create Your Workspace" to sign up your organization
   - Fill in your organization details and admin account
   - Start managing projects!

6. **Optional: Create additional admin user via CLI:**
```bash
docker compose exec web flask create-admin
```

### First Time Setup

1. **Sign up your organization at** `http://localhost:5987/org/signup`
   - Organization name (e.g., "Acme Inc")
   - Subdomain (e.g., "acme")
   - Admin email and password

2. **You'll get:**
   - Unlimited team members
   - Unlimited projects
   - All features enabled
   - Full admin access

3. **Start creating:**
   - Create your first project
   - Add team members via invitations
   - Create issues and start tracking work

### Accessing from External Domain (Cloudflare Tunnel, Nginx)

This application is fully compatible with reverse proxies including:
- **Cloudflare Tunnel** ✅
- **Nginx with SSL** ✅
- **Traefik** ✅
- **Apache** ✅

The app automatically handles proxy headers (`X-Forwarded-Proto`, `X-Forwarded-For`) and works correctly with HTTPS termination at the proxy level.

### Manual Installation (Development)

1. **Create virtual environment:**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL database:**
```bash
# Install PostgreSQL if needed
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
# or
brew install postgresql@15  # macOS

# Create database
sudo -u postgres psql
CREATE DATABASE projectmanager;
CREATE USER projectmgr WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE projectmanager TO projectmgr;
\q
```

4. **Set up environment:**
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL=postgresql://projectmgr:your_password@localhost/projectmanager
```

5. **Initialize database:**
```bash
flask db upgrade
```

6. **Run development server:**
```bash
flask run --debug --port 5987
```

7. **Access at** `http://localhost:5987`

## ⚙️ Configuration

### Environment Variables

**Required Variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key (use random hex) | `abc123...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |

**Application Settings:**

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `production` |
| `APP_NAME` | Application display name | `ProjectFlow` |
| `APP_URL` | Base URL for the application | `http://localhost:5987` |

**Database Settings:**

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | `projectmgr` |
| `DB_PASSWORD` | PostgreSQL password | Required |
| `DB_NAME` | Database name | `projectmanager` |

**Email Configuration (Optional but recommended):**

| Variable | Description | Default |
|----------|-------------|---------|
| `MAIL_SERVER` | SMTP server hostname | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USE_TLS` | Use TLS encryption | `true` |
| `MAIL_USERNAME` | SMTP username/email | Required for email |
| `MAIL_PASSWORD` | SMTP password/app password | Required for email |
| `MAIL_DEFAULT_SENDER` | Default sender email | `noreply@example.com` |

**Slack Integration (Optional):**

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Webhook URL from Slack App |
| `SLACK_ENABLED` | Enable Slack notifications (`true`/`false`) |
| `SLACK_DEFAULT_CHANNEL` | Default channel for notifications |
| `SLACK_CHANNEL_BUGS` | Channel for bug notifications |
| `SLACK_CHANNEL_FEATURES` | Channel for feature notifications |

**GitHub Integration (Optional):**

| Variable | Description |
|----------|-------------|
| `GITHUB_CLIENT_ID` | OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | OAuth App Client Secret |
| `GITHUB_OAUTH_ENABLED` | Enable GitHub OAuth (`true`/`false`) |

**AWS Bedrock AI (Optional):**

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | AWS region (e.g., `us-east-1`) |
| `BEDROCK_MODEL_ID` | Model ID (default: Claude 3 Sonnet) |

### Setting Up Integrations

#### Email (Gmail Example)

1. **Enable 2-factor authentication** on your Gmail account
2. **Create an App Password:**
   - Go to Google Account Settings → Security
   - Select "2-Step Verification" → "App passwords"
   - Generate a new app password
3. **Add to your `.env`:**
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

#### Slack Integration

1. **Create a Slack App:**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name it (e.g., "ProjectFlow") and select your workspace
   
2. **Enable Incoming Webhooks:**
   - In your app settings, go to "Incoming Webhooks"
   - Toggle "Activate Incoming Webhooks" to On
   - Click "Add New Webhook to Workspace"
   - Select a channel and authorize
   
3. **Copy the webhook URL** and add to `.env`:
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_ENABLED=true
SLACK_DEFAULT_CHANNEL=#general
SLACK_CHANNEL_BUGS=#bugs
SLACK_CHANNEL_FEATURES=#features
```

#### GitHub OAuth Login

1. **Register OAuth App:**
   - Go to GitHub Settings → Developer Settings → OAuth Apps
   - Click "New OAuth App"
   - Set:
     - Application name: `ProjectFlow`
     - Homepage URL: `https://your-domain.com`
     - Authorization callback URL: `https://your-domain.com/auth/github/callback`
   
2. **Add credentials to `.env`:**
```env
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_OAUTH_ENABLED=true
```

## Project Structure

```
project_manager/
├── app.py                 # Application factory
├── config.py              # Configuration classes
├── extensions.py          # Flask extensions
├── models.py              # Database models
├── routes/
│   ├── auth.py           # Authentication routes
│   ├── dashboard.py      # Dashboard routes
│   ├── issues.py         # Issue management
│   ├── projects.py       # Project management
│   ├── admin.py          # Admin panel
│   └── api.py            # REST API
├── services/
│   ├── slack_service.py  # Slack notifications
│   ├── github_service.py # GitHub integration
│   └── email_service.py  # Email notifications
├── templates/            # Jinja2 templates
├── static/
│   ├── css/style.css    # Custom styles
│   ├── js/main.js       # JavaScript
│   └── img/             # Images
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/login          # User login (returns JWT token)
POST   /api/auth/register       # User registration
POST   /api/auth/logout         # Logout (invalidate token)
GET    /api/auth/me             # Get current user info
```

### Issues
```
GET    /api/issues              # List issues (with filters)
POST   /api/issues              # Create new issue
GET    /api/issues/<id>         # Get issue details
PUT    /api/issues/<id>         # Update issue
DELETE /api/issues/<id>         # Delete issue
POST   /api/issues/<id>/comment # Add comment
GET    /api/issues/<id>/history # Get change history
```

### Projects
```
GET    /api/projects            # List projects in organization
POST   /api/projects            # Create new project
GET    /api/projects/<id>       # Get project details
PUT    /api/projects/<id>       # Update project
DELETE /api/projects/<id>       # Delete project
GET    /api/projects/<id>/stats # Get project statistics
```

### Organizations
```
GET    /api/organizations       # List user's organizations
POST   /api/organizations       # Create organization
GET    /api/organizations/<id>  # Get organization details
PUT    /api/organizations/<id>  # Update organization settings
GET    /api/organizations/<id>/members  # List members
POST   /api/organizations/<id>/invite   # Invite member
```

### Users (Admin Only)
```
GET    /api/users               # List all users
POST   /api/users               # Create user
GET    /api/users/<id>          # Get user details
PUT    /api/users/<id>          # Update user
DELETE /api/users/<id>          # Deactivate user
```

**Authentication:**
- Use JWT tokens in `Authorization: Bearer <token>` header
- Tokens expire after 24 hours (configurable)
- Refresh tokens valid for 30 days

**Example API Request:**
```bash
# Login
curl -X POST http://localhost:5987/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Create Issue
curl -X POST http://localhost:5987/api/issues \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "title": "Bug in login",
    "description": "Users cannot login",
    "priority": "high",
    "issue_type": "bug"
  }'
```

## 👥 User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, manage all organizations, users, and settings |
| **Organization Owner** | Full access within their organization, manage members and subscription |
| **Project Manager** | Create/manage projects, add members, configure project settings |
| **Developer** | Create/edit issues, comment, update status, manage own assignments |
| **Viewer** | Read-only access to projects and issues |

## 🔒 Multi-Tenancy & Data Isolation

Each organization has **complete data isolation**:
- **Separate Database Records**: All data is filtered by `organization_id`
- **No Cross-Organization Access**: Users can only see data from their current organization
- **Secure Queries**: All database queries include organization filters
- **Invitation-Only**: Users must be invited to access an organization

## 🚀 Production Deployment

### Option 1: Docker with Cloudflare Tunnel (Recommended)

**Perfect for:**
- No public IP or behind firewall
- SSL/HTTPS handled by Cloudflare
- DDoS protection included

**Setup:**

1. **Create Cloudflare Tunnel:**
   ```bash
   cloudflared tunnel create projectflow
   ```

2. **Configure tunnel** to point to `http://localhost:5987`

3. **Start application:**
   ```bash
   docker compose up -d
   ```

4. **No additional configuration needed!** 
   - The app automatically detects proxy headers
   - CSRF tokens work correctly with Cloudflare
   - Secure cookies handled properly

### Option 2: Docker with Nginx and SSL

**Perfect for:**
- Custom domain with direct access
- Full control over SSL certificates

**Setup:**

1. **Place SSL certificates** in `ssl/` directory:
   - `ssl/fullchain.pem`
   - `ssl/privkey.pem`

2. **Update nginx.conf** with your domain

3. **Start with production profile:**
   ```bash
   docker compose --profile production up -d
   ```

### Option 3: Systemd Service (Manual)

1. **Create service file** `/etc/systemd/system/projectflow.service`:
```ini
[Unit]
Description=ProjectFlow Application
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/projectflow
Environment="PATH=/opt/projectflow/venv/bin"
ExecStart=/opt/projectflow/venv/bin/gunicorn -w 4 -b 127.0.0.1:5987 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Enable and start:**
```bash
sudo systemctl enable projectflow
sudo systemctl start projectflow
```

### Production Security Checklist

- [ ] Change `SECRET_KEY` to a secure random value (`openssl rand -hex 32`)
- [ ] Use strong database password (minimum 16 characters)
- [ ] Enable HTTPS (via Cloudflare Tunnel, nginx, or Let's Encrypt)
- [ ] Set `FLASK_ENV=production` in environment
- [ ] Configure firewall rules (only expose necessary ports)
- [ ] Set up automated database backups
- [ ] Enable Redis for rate limiting (recommended)
- [ ] Review and restrict CORS settings if using API
- [ ] Configure proper file upload size limits
- [ ] Set up monitoring and logging
- [ ] Enable SSL for database connections
- [ ] Use environment variables (never commit secrets to git)

### Database Backups

**Automated backup script:**
```bash
#!/bin/bash
# backup-db.sh
BACKUP_DIR="/backups/projectflow"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="projectflow_backup_$DATE.sql"

mkdir -p $BACKUP_DIR
docker compose exec -T db pg_dump -U projectmgr projectmanager > "$BACKUP_DIR/$FILENAME"
gzip "$BACKUP_DIR/$FILENAME"

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

**Restore from backup:**
```bash
gunzip -c backup.sql.gz | docker compose exec -T db psql -U projectmgr projectmanager
```

## 🐛 Troubleshooting

### CSRF Token Missing Error

**Problem:** Form submission fails with "CSRF token missing"

**Solution:**
- Ensure `SECRET_KEY` is set in environment
- If behind Cloudflare Tunnel/proxy, verify `ProxyFix` is configured (already set in app.py)
- Clear browser cookies and try again
- Check that cookies are enabled in browser

### Can't See Projects from My Organization

**Problem:** Projects or issues from other organizations are visible

**Solution:**
- Clear application cache: `docker compose restart web`
- Log out and log back in
- Verify `current_organization_id` is set for your user
- Check database: `SELECT current_organization_id FROM users WHERE email='your@email.com';`

### Database Connection Failed

**Problem:** Application can't connect to PostgreSQL

**Solution:**
```bash
# Check if PostgreSQL container is running
docker compose ps

# Check database logs
docker compose logs db

# Verify connection string
docker compose exec web env | grep DATABASE_URL

# Test connection manually
docker compose exec db psql -U projectmgr -d projectmanager
```

### Email Not Sending

**Problem:** Email notifications not working

**Solution:**
- Verify SMTP credentials are correct
- For Gmail, use App Password (not regular password)
- Check if MAIL_USE_TLS is set to `true`
- Test SMTP connection:
```bash
docker compose exec web python -c "
from extensions import mail
from flask_mail import Message
from app import create_app
app = create_app()
with app.app_context():
    msg = Message('Test', recipients=['test@example.com'])
    mail.send(msg)
"
```

### Container Won't Start

**Problem:** Docker container exits immediately

**Solution:**
```bash
# Check logs for errors
docker compose logs web

# Verify environment variables
docker compose config

# Check database is healthy
docker compose exec db pg_isready -U projectmgr

# Rebuild without cache
docker compose build --no-cache web
docker compose up -d
```

### Slow Performance

**Problem:** Application is slow or unresponsive

**Solutions:**
- Enable Redis for rate limiting and caching
- Check database indexes: `docker compose exec web flask db upgrade`
- Monitor resource usage: `docker stats`
- Increase worker count in docker-compose.yml
- Add database connection pooling
- Enable query optimization

### Port Already in Use

**Problem:** Port 5987 is already in use

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :5987

# Change port in docker-compose.yml
ports:
  - "8080:5000"  # Use 8080 instead

# Or stop the conflicting service
sudo systemctl stop <service-name>
```

## 🛠️ Development

### Running Tests
```bash
# Inside Docker
docker compose exec web pytest tests/ -v

# Or locally
pytest tests/ -v --cov=app
```

### Database Migrations

**Create new migration:**
```bash
docker compose exec web flask db migrate -m "Add new feature"
```

**Apply migrations:**
```bash
docker compose exec web flask db upgrade
```

**Rollback migration:**
```bash
docker compose exec web flask db downgrade
```

### Creating Test Data

**Create admin user:**
```bash
docker compose exec web flask create-admin
```

**Create sample organization:**
```bash
docker compose exec web python -c "
from app import create_app
from extensions import db
from models import Organization, User, SubscriptionPlan
app = create_app()
with app.app_context():
    org = Organization(name='Test Org', slug='test-org', subdomain='test')
    db.session.add(org)
    db.session.commit()
    print(f'Created organization: {org.name}')
"
```

### Code Style

```bash
# Format code
black .

# Check linting
flake8 --max-line-length=120

# Sort imports
isort .
```

### Debugging

**Enable debug mode:**
```bash
# In .env
FLASK_ENV=development

# Restart
docker compose restart web

# View detailed logs
docker compose logs -f web
```

**Access Python shell in container:**
```bash
docker compose exec web flask shell
```

## 📁 Project Structure

```
project_manager/
├── app.py                      # Application factory and entry point
├── config.py                   # Configuration classes (Dev, Prod, Test)
├── extensions.py               # Flask extensions initialization
├── models.py                   # SQLAlchemy database models
│
├── routes/                     # Application routes/blueprints
│   ├── __init__.py
│   ├── auth.py                # Authentication (login, register, password reset)
│   ├── dashboard.py           # User dashboard and analytics
│   ├── issues.py              # Issue CRUD, kanban, comments
│   ├── projects.py            # Project management, sprints, epics
│   ├── admin.py               # Admin panel and settings
│   ├── organization.py        # Multi-tenant organization management
│   ├── wiki.py                # Wiki pages per project
│   └── api.py                 # REST API endpoints
│
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── slack_service.py       # Slack webhook notifications
│   ├── github_service.py      # GitHub API integration
│   ├── email_service.py       # Email notifications
│   └── bedrock_service.py     # AWS Bedrock AI integration
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html              # Base template with header/footer
│   ├── landing.html           # Landing page
│   ├── auth/                  # Login, register, password reset
│   ├── dashboard/             # Dashboard views
│   ├── issues/                # Issue list, kanban, view, edit
│   ├── projects/              # Project views
│   ├── admin/                 # Admin panel
│   ├── organization/          # Organization settings
│   ├── wiki/                  # Wiki pages
│   ├── errors/                # Error pages (404, 500)
│   └── partials/              # Reusable template components
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Custom styles
│   ├── js/
│   │   └── main.js            # Custom JavaScript
│   └── img/                   # Images and logos
│
├── migrations/                 # Alembic database migrations
│   ├── versions/              # Migration version files
│   ├── alembic.ini
│   └── env.py
│
├── tests/                      # Unit and integration tests
├── uploads/                    # User uploaded files (gitignored)
│
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-container orchestration
├── nginx.conf                  # Nginx reverse proxy config
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (gitignored)
└── README.md                   # This file
```

## 📊 Features Roadmap

### Current (v1.0)
- ✅ Multi-tenant organizations
- ✅ Project & Issue management
- ✅ Kanban board
- ✅ Sprints, Epics, Components
- ✅ Wiki pages
- ✅ Comments & file attachments
- ✅ Slack & GitHub integration
- ✅ Email notifications
- ✅ Role-based access control

### Planned (v1.1)
- [ ] Time tracking
- [ ] Gantt chart view
- [ ] Advanced reporting & charts
- [ ] Mobile app (React Native)
- [ ] Webhooks for external integrations
- [ ] Activity timeline view
- [ ] File preview for images/PDFs
- [ ] @mentions in comments
- [ ] Issue dependencies & blocking

### Future (v2.0)
- [ ] Real-time collaboration (WebSockets)
- [ ] Automated testing integration
- [ ] CI/CD pipeline visualization
- [ ] Custom fields per project
- [ ] Workflow automation
- [ ] Integration marketplace
- [ ] AI-powered insights
- [ ] Multi-language support

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
   ```bash
   git clone https://github.com/stwins60/projectflow.git
   cd projectflow
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Write clean, documented code
   - Follow PEP 8 style guide
   - Add tests for new features
   - Update README if needed

4. **Test your changes**
   ```bash
   pytest tests/ -v
   black .
   flake8 --max-line-length=120
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Submit a Pull Request**
   - Describe your changes clearly
   - Reference any related issues
   - Wait for review

### Contribution Guidelines

- **Code Style**: Follow PEP 8, use Black formatter
- **Commits**: Write clear, descriptive commit messages
- **Tests**: Add tests for new functionality
- **Documentation**: Update docs for new features
- **Issues**: Check existing issues before opening new ones
- **Be Respectful**: Follow our code of conduct

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 💬 Support & Community

- **Issues**: [GitHub Issues](https://github.com/stwins60/projectflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/stwins60/projectflow/discussions)


## 🙏 Acknowledgments

Built with:
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap 5](https://getbootstrap.com/) - UI framework
- [PostgreSQL](https://www.postgresql.org/) - Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Gunicorn](https://gunicorn.org/) - WSGI server
- [Docker](https://www.docker.com/) - Containerization

## 🔗 Related Documentation

- [INVITATION_SYSTEM.md](docs/INVITATION_SYSTEM.md) - How the invitation system works
- [JIRA_TICKETS.md](docs/JIRA_TICKETS.md) - Importing from Jira
- [SLACK_NOTIFICATIONS.md](docs/SLACK_NOTIFICATIONS.md) - Slack integration details
- [SAAS_FEATURES.md](docs/SAAS_FEATURES.md) - Multi-tenancy architecture
- [ADDING_USERS_GUIDE.md](docs/ADDING_USERS_GUIDE.md) - Guide for adding users to organizations

---

**Made with ❤️ by developers, for developers**
