"""
Email service for sending notifications via SMTP.
"""
from flask import current_app, render_template, url_for
from flask_mail import Message
from extensions import mail
from models import Settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def get_smtp_config():
    """Get SMTP configuration from settings or config."""
    return {
        'server': Settings.get('smtp_server') or current_app.config.get('MAIL_SERVER'),
        'port': int(Settings.get('smtp_port') or current_app.config.get('MAIL_PORT', 587)),
        'username': Settings.get('smtp_username') or current_app.config.get('MAIL_USERNAME'),
        'password': Settings.get('smtp_password') or current_app.config.get('MAIL_PASSWORD'),
        'use_tls': (Settings.get('smtp_use_tls', 'true').lower() == 'true') or 
                   current_app.config.get('MAIL_USE_TLS', True),
        'sender': Settings.get('smtp_sender') or current_app.config.get('MAIL_DEFAULT_SENDER'),
    }


def send_email(to, subject, html_content, text_content=None):
    """Send an email using Flask-Mail or direct SMTP."""
    config = get_smtp_config()
    
    if not config['server'] or not config['username']:
        current_app.logger.warning('Email not configured, skipping send')
        return False
    
    try:
        msg = Message(
            subject=subject,
            sender=config['sender'],
            recipients=[to] if isinstance(to, str) else to
        )
        msg.html = html_content
        if text_content:
            msg.body = text_content
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'Failed to send email: {e}')
        # Try direct SMTP as fallback
        return send_email_smtp(to, subject, html_content, text_content)


def send_email_smtp(to, subject, html_content, text_content=None):
    """Send email using direct SMTP connection."""
    config = get_smtp_config()
    
    if not config['server'] or not config['username']:
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config['sender']
        msg['To'] = to if isinstance(to, str) else ', '.join(to)
        
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        if config['use_tls']:
            server = smtplib.SMTP(config['server'], config['port'])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config['server'], config['port'])
        
        server.login(config['username'], config['password'])
        server.sendmail(config['sender'], [to] if isinstance(to, str) else to, msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        current_app.logger.error(f'SMTP send failed: {e}')
        return False


def send_verification_email(user):
    """Send email verification link to user."""
    verify_url = url_for('auth.verify_email', token=user.verification_token, _external=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
            .button {{ 
                display: inline-block; 
                padding: 14px 32px; 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                text-decoration: none; 
                border-radius: 8px;
                margin: 20px 0;
            }}
            .footer {{ color: #666; font-size: 14px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">ProjectFlow</div>
            </div>
            <h2>Verify Your Email Address</h2>
            <p>Hi {user.username},</p>
            <p>Welcome to ProjectFlow! Please verify your email address to complete your registration.</p>
            <p style="text-align: center;">
                <a href="{verify_url}" class="button">Verify Email</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #6366f1;">{verify_url}</p>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Verify Your Email Address
    
    Hi {user.username},
    
    Welcome to ProjectFlow! Please verify your email address by clicking the link below:
    
    {verify_url}
    
    If you didn't create an account, you can safely ignore this email.
    
    © 2026 ProjectFlow. All rights reserved.
    """
    
    return send_email(user.email, 'Verify Your Email - ProjectFlow', html_content, text_content)


def send_password_reset_email(user, token):
    """Send password reset email to user."""
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
            .button {{ 
                display: inline-block; 
                padding: 14px 32px; 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                text-decoration: none; 
                border-radius: 8px;
                margin: 20px 0;
            }}
            .warning {{ 
                background: #fef3c7; 
                border-left: 4px solid #f59e0b; 
                padding: 12px; 
                margin: 20px 0; 
            }}
            .footer {{ color: #666; font-size: 14px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">ProjectFlow</div>
            </div>
            <h2>Reset Your Password</h2>
            <p>Hi {user.username},</p>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <div class="warning">
                <strong>This link will expire in 24 hours.</strong>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #6366f1;">{reset_url}</p>
            <div class="footer">
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Reset Your Password
    
    Hi {user.username},
    
    We received a request to reset your password. Click the link below to create a new password:
    
    {reset_url}
    
    This link will expire in 24 hours.
    
    If you didn't request a password reset, you can safely ignore this email.
    
    © 2026 ProjectFlow. All rights reserved.
    """
    
    return send_email(user.email, 'Reset Your Password - ProjectFlow', html_content, text_content)


def send_issue_assignment_email(issue, assignee, assigner):
    """Send email notification when issue is assigned."""
    issue_url = url_for('issues.view', issue_id=issue.id, _external=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
            .issue-card {{
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
            }}
            .issue-key {{
                color: #6366f1;
                font-weight: 600;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
            }}
            .priority-high {{ background: #fef2f2; color: #dc2626; }}
            .priority-medium {{ background: #fefce8; color: #ca8a04; }}
            .priority-low {{ background: #f0fdf4; color: #16a34a; }}
            .button {{ 
                display: inline-block; 
                padding: 12px 24px; 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                text-decoration: none; 
                border-radius: 8px;
            }}
            .footer {{ color: #666; font-size: 14px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">ProjectFlow</div>
            </div>
            <h2>Issue Assigned to You</h2>
            <p>Hi {assignee.username},</p>
            <p>{assigner.username} has assigned you the following issue:</p>
            
            <div class="issue-card">
                <p><span class="issue-key">{issue.key}</span></p>
                <h3 style="margin: 8px 0;">{issue.title}</h3>
                <p>
                    <span class="badge priority-{issue.priority.value}">{issue.priority.value.title()}</span>
                    &nbsp;&middot;&nbsp;
                    {issue.project.name}
                </p>
                {f'<p style="color: #666;">{issue.description[:200]}...</p>' if issue.description else ''}
            </div>
            
            <p style="text-align: center;">
                <a href="{issue_url}" class="button">View Issue</a>
            </p>
            
            <div class="footer">
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        assignee.email, 
        f'[{issue.key}] Issue Assigned: {issue.title}', 
        html_content
    )


def send_due_date_reminder(issue, assignee):
    """Send due date reminder email."""
    issue_url = url_for('issues.view', issue_id=issue.id, _external=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
            .warning {{ 
                background: #fef3c7; 
                border-left: 4px solid #f59e0b; 
                padding: 16px; 
                border-radius: 8px;
                margin: 20px 0;
            }}
            .button {{ 
                display: inline-block; 
                padding: 12px 24px; 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                text-decoration: none; 
                border-radius: 8px;
            }}
            .footer {{ color: #666; font-size: 14px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">ProjectFlow</div>
            </div>
            <h2>⏰ Due Date Reminder</h2>
            <p>Hi {assignee.username},</p>
            
            <div class="warning">
                <strong>Issue {issue.key} is due on {issue.due_date.strftime('%B %d, %Y')}</strong>
            </div>
            
            <p><strong>Title:</strong> {issue.title}</p>
            <p><strong>Project:</strong> {issue.project.name}</p>
            <p><strong>Priority:</strong> {issue.priority.value.title()}</p>
            
            <p style="text-align: center; margin-top: 30px;">
                <a href="{issue_url}" class="button">View Issue</a>
            </p>
            
            <div class="footer">
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        assignee.email, 
        f'⏰ Reminder: [{issue.key}] Due {issue.due_date.strftime("%B %d")}', 
        html_content
    )


def send_weekly_summary(user, summary_data):
    """Send weekly project summary email."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
            .stat-card {{
                display: inline-block;
                padding: 20px;
                background: #f8fafc;
                border-radius: 12px;
                margin: 10px;
                text-align: center;
                min-width: 100px;
            }}
            .stat-value {{ font-size: 32px; font-weight: bold; color: #6366f1; }}
            .stat-label {{ font-size: 12px; color: #666; }}
            .footer {{ color: #666; font-size: 14px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">ProjectFlow</div>
            </div>
            <h2>📊 Your Weekly Summary</h2>
            <p>Hi {user.username},</p>
            <p>Here's your activity summary for the past week:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <div class="stat-card">
                    <div class="stat-value">{summary_data.get('completed', 0)}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary_data.get('in_progress', 0)}</div>
                    <div class="stat-label">In Progress</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary_data.get('created', 0)}</div>
                    <div class="stat-label">Created</div>
                </div>
            </div>
            
            <div class="footer">
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(user.email, '📊 Your Weekly Summary - ProjectFlow', html_content)


def send_invitation_email(invitation, invited_by):
    """Send an invitation email to a new user."""
    invitation_url = url_for('auth.accept_invitation', 
                              token=invitation.token, 
                              _external=True)
    
    role_display = invitation.role.value.replace('_', ' ').title()
    expires_date = invitation.expires_at.strftime('%B %d, %Y')
    organization_name = invitation.organization.name if invitation.organization else 'Default Organization'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 30px auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .invitation-box {{
                background-color: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .invitation-box p {{
                margin: 5px 0;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                text-align: center;
                margin: 20px 0;
                transition: transform 0.2s;
            }}
            .button:hover {{
                transform: translateY(-2px);
            }}
            .info-text {{
                color: #666;
                font-size: 14px;
                margin-top: 20px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <span>🎉</span>
                    <span>You're Invited!</span>
                </h1>
            </div>
            
            <div class="content">
                <p>Hello,</p>
                
                <p><strong>{invited_by.first_name or invited_by.username}</strong> has invited you to join <strong>ProjectFlow</strong> - a collaborative project management platform.</p>
                
                <div class="invitation-box">
                    <p><strong>🏢 Organization:</strong> {organization_name}</p>
                    <p><strong>📧 Email:</strong> {invitation.email}</p>
                    <p><strong>👤 Role:</strong> {role_display}</p>
                    <p><strong>⏰ Valid Until:</strong> {expires_date}</p>
                </div>
                
                <p>Click the button below to accept your invitation and create your account:</p>
                
                <div style="text-align: center;">
                    <a href="{invitation_url}" class="button">Accept Invitation & Register</a>
                </div>
                
                <p class="info-text">
                    This invitation will expire on {expires_date}. If you didn't expect this invitation, you can safely ignore this email.
                </p>
                
                <p class="info-text">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{invitation_url}" style="color: #667eea; word-break: break-all;">{invitation_url}</a>
                </p>
            </div>
            
            <div class="footer">
                <p>&copy; 2026 ProjectFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    You're Invited to ProjectFlow!
    
    {invited_by.first_name or invited_by.username} has invited you to join ProjectFlow as a {role_display}.
    
    Email: {invitation.email}
    Role: {role_display}
    Valid Until: {expires_date}
    
    Accept your invitation by visiting:
    {invitation_url}
    
    This invitation will expire on {expires_date}. If you didn't expect this invitation, you can safely ignore this email.
    """
    
    return send_email(
        invitation.email, 
        f'🎉 You\'re invited to join ProjectFlow', 
        html_content, 
        text_content
    )

