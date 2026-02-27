"""
Slack integration service for sending notifications.
Supports both Webhook and Bot Token approaches.
"""
import json
import requests
from flask import current_app
from models import Settings


def get_slack_webhook_url():
    """Get Slack webhook URL from settings or config."""
    url = Settings.get('slack_webhook_url')
    if not url:
        url = current_app.config.get('SLACK_WEBHOOK_URL')
    return url


def get_slack_bot_token():
    """Get Slack bot token from settings or config."""
    token = Settings.get('slack_bot_token')
    if not token:
        token = current_app.config.get('SLACK_BOT_TOKEN')
    return token


def is_slack_enabled():
    """Check if Slack notifications are enabled."""
    enabled = Settings.get('slack_enabled', 'false').lower() == 'true'
    if not enabled:
        enabled = current_app.config.get('SLACK_ENABLED', False)
    return enabled


def get_channel_for_issue_type(issue_type):
    """Get the Slack channel for a specific issue type."""
    # Get custom channel mapping from settings or use defaults
    channel_mapping = {
        'bug': Settings.get('slack_channel_bugs') or current_app.config.get('SLACK_CHANNEL_BUGS', '#bugs'),
        'feature': Settings.get('slack_channel_features') or current_app.config.get('SLACK_CHANNEL_FEATURES', '#features'),
        'task': Settings.get('slack_channel_tasks') or current_app.config.get('SLACK_CHANNEL_TASKS', '#tasks'),
        'story': Settings.get('slack_channel_stories') or current_app.config.get('SLACK_CHANNEL_STORIES', '#features'),
    }
    
    # Get default channel as fallback
    default_channel = Settings.get('slack_default_channel') or current_app.config.get('SLACK_DEFAULT_CHANNEL', '#general')
    
    return channel_mapping.get(issue_type, default_channel)


def send_slack_message_via_bot(message, blocks=None, channel='#general'):
    """Send a message to Slack using Bot Token (chat.postMessage API)."""
    bot_token = get_slack_bot_token()
    
    if not bot_token:
        return False
    
    # Use Slack Web API
    url = 'https://slack.com/api/chat.postMessage'
    
    payload = {
        'channel': channel,
        'text': message
    }
    
    if blocks:
        payload['blocks'] = blocks
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': f'Bearer {bot_token}'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        
        if not result.get('ok'):
            error = result.get('error', 'unknown error')
            current_app.logger.error(f'Slack API error: {error}')
            return False
        
        return True
    except requests.RequestException as e:
        current_app.logger.error(f'Slack bot notification failed: {e}')
        return False


def send_slack_message_via_webhook(message, blocks=None, channel=None):
    """Send a message to Slack using Webhook (legacy/fallback)."""
    webhook_url = get_slack_webhook_url()
    
    if not webhook_url:
        return False
    
    payload = {'text': message}
    if blocks:
        payload['blocks'] = blocks
    if channel:
        payload['channel'] = channel  # Note: may not work with all webhooks
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException as e:
        current_app.logger.error(f'Slack webhook notification failed: {e}')
        return False


def send_slack_message(message, blocks=None, channel=None):
    """Send a message to Slack (auto-detects bot token or webhook)."""
    if not is_slack_enabled():
        return False
    
    # Prefer bot token over webhook (more flexible)
    bot_token = get_slack_bot_token()
    
    if bot_token:
        # Use bot token API
        if not channel:
            channel = Settings.get('slack_default_channel') or current_app.config.get('SLACK_DEFAULT_CHANNEL', '#general')
        return send_slack_message_via_bot(message, blocks, channel)
    else:
        # Fallback to webhook
        return send_slack_message_via_webhook(message, blocks, channel)


def send_slack_notification(event_type, **kwargs):
    """Send a formatted Slack notification based on event type."""
    if not is_slack_enabled():
        current_app.logger.info('Slack notifications are disabled')
        return False
    
    current_app.logger.info(f'Sending Slack notification: {event_type}')
    
    message = ''
    blocks = []
    
    if event_type == 'issue_created':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        
        message = f"🆕 New issue created: {issue.key}"
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🆕 New Issue Created"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{issue.project.name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Created by:*\n{user.username}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority:*\n{get_priority_emoji(issue.priority.value)} {issue.priority.value.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{issue.issue_type.value.title()}"
                    }
                ]
            }
        ]
    
    elif event_type == 'status_updated':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        old_status = kwargs.get('old_status')
        new_status = kwargs.get('new_status')
        
        message = f"📝 Issue {issue.key} status changed"
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📝 Issue Status Updated"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status Change:*\n{format_status(old_status)} → {format_status(new_status)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Updated by:*\n{user.username}"
                    }
                ]
            }
        ]
    
    elif event_type == 'issue_assigned':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        assignee = kwargs.get('assignee')
        
        message = f"👤 Issue {issue.key} assigned to {assignee.username}"
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👤 Issue Assigned"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Assigned to:*\n{assignee.username}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Assigned by:*\n{user.username}"
                    }
                ]
            }
        ]
    
    elif event_type == 'comment_added':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        comment = kwargs.get('comment')
        
        # Truncate comment if too long
        content = comment.content[:200] + '...' if len(comment.content) > 200 else comment.content
        
        message = f"💬 New comment on {issue.key}"
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💬 New Comment"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Comment by:*\n{user.username}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f">{content}"
                }
            }
        ]
    
    elif event_type == 'issue_updated':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        changes = kwargs.get('changes', [])
        
        message = f"✏️ Issue {issue.key} updated"
        
        # Build fields for changes
        change_fields = [
            {
                "type": "mrkdwn",
                "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
            },
            {
                "type": "mrkdwn",
                "text": f"*Title:*\n{issue.title}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Updated by:*\n{user.username}"
            }
        ]
        
        # Add priority if present
        if hasattr(issue, 'priority'):
            change_fields.append({
                "type": "mrkdwn",
                "text": f"*Priority:*\n{get_priority_emoji(issue.priority.value)} {issue.priority.value.title()}"
            })
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✏️ Issue Updated"
                }
            },
            {
                "type": "section",
                "fields": change_fields
            }
        ]
        
        # Add changes section if there are specific changes
        if changes:
            changes_text = "\n".join([f"• *{change['field'].replace('_', ' ').title()}:* {change.get('old', 'N/A')} → {change.get('new', 'N/A')}" for change in changes[:5]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Changes:*\n{changes_text}"
                }
            })
    
    elif event_type == 'priority_changed':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        old_priority = kwargs.get('old_priority')
        new_priority = kwargs.get('new_priority')
        
        message = f"⚡ Issue {issue.key} priority changed"
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚡ Priority Changed"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority Change:*\n{get_priority_emoji(old_priority)} {old_priority.title()} → {get_priority_emoji(new_priority)} {new_priority.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Changed by:*\n{user.username}"
                    }
                ]
            }
        ]
    
    elif event_type == 'labels_changed':
        issue = kwargs.get('issue')
        user = kwargs.get('user')
        added_labels = kwargs.get('added_labels', [])
        removed_labels = kwargs.get('removed_labels', [])
        
        message = f"🏷️ Issue {issue.key} labels updated"
        
        label_changes = []
        if added_labels:
            label_changes.append(f"*Added:* {', '.join([l.name for l in added_labels])}")
        if removed_labels:
            label_changes.append(f"*Removed:* {', '.join([l.name for l in removed_labels])}")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🏷️ Labels Updated"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue:*\n<{get_issue_url(issue)}|{issue.key}>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{issue.title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Updated by:*\n{user.username}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(label_changes)
                }
            }
        ]
    
    # Determine channel based on issue type (for issue-related events)
    channel = None
    issue = kwargs.get('issue')
    if issue and hasattr(issue, 'issue_type'):
        # issue_type is an Enum, get its value
        issue_type_value = issue.issue_type.value if hasattr(issue.issue_type, 'value') else str(issue.issue_type)
        channel = get_channel_for_issue_type(issue_type_value)
        current_app.logger.info(f'Sending to channel: {channel} for issue type: {issue_type_value}')
    
    result = send_slack_message(message, blocks, channel=channel)
    current_app.logger.info(f'Slack notification result: {result}')
    return result


def get_issue_url(issue):
    """Get the URL for an issue."""
    # This would be configured based on your deployment
    base_url = current_app.config.get('APP_URL', 'http://localhost:5000')
    return f"{base_url}/issues/{issue.id}"


def get_priority_emoji(priority):
    """Get emoji for priority level."""
    emojis = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }
    return emojis.get(priority, '⚪')


def format_status(status):
    """Format status for display."""
    status_labels = {
        'backlog': '📋 Backlog',
        'todo': '📝 To Do',
        'in_progress': '🔄 In Progress',
        'code_review': '👀 Code Review',
        'done': '✅ Done'
    }
    return status_labels.get(status, status)
