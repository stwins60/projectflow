# Slack Notifications Setup

This project manager includes comprehensive Slack notifications for all ticket updates using the **Slack Bot Token** approach for maximum flexibility.

## 🚀 Quick Start

1. **Create a Slack App**:
   - Go to https://api.slack.com/apps → **Create New App** → **From scratch**
   - Name it "Project Manager Bot"
   - Select your workspace

2. **Add Bot Permissions**:
   - Go to **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**
   - Add: `chat:write` and `chat:write.public`

3. **Install to Workspace**:
   - Click **Install to Workspace** → **Allow**
   - Copy the **Bot User OAuth Token** (starts with `xoxb-`)

4. **Configure Environment**:
   ```bash
   # Add to .env file
   SLACK_BOT_TOKEN=xoxb-your-copied-token-here
   SLACK_ENABLED=true
   SLACK_CHANNEL_BUGS=#bugs
   SLACK_CHANNEL_FEATURES=#features
   ```

5. **Invite Bot to Channels**:
   ```
   # In each Slack channel, type:
   /invite @Project Manager Bot
   ```

6. **Restart Application**:
   ```bash
   docker compose restart web
   ```

7. **Enable in Projects**:
   - Admin → Projects → Edit → Enable "Slack Notifications"

✅ **Done!** Create a test issue and watch notifications flow!

---

## Features

### Notification Types

1. **Issue Created** 🆕
   - Triggered when a new issue is created
   - Shows issue key, title, project, creator, priority, and type

2. **Status Updated** 📝
   - Triggered when issue status changes (Backlog → To Do → In Progress → Code Review → Done)
   - Shows the status transition with emojis

3. **Priority Changed** ⚡
   - Triggered when issue priority changes
   - Shows old and new priority with color-coded emojis

4. **Issue Assigned** 👤
   - Triggered when an issue is assigned to someone
   - Shows who assigned and who was assigned

5. **Labels Changed** 🏷️
   - Triggered when labels are added or removed from an issue
   - Lists added and removed labels

6. **Issue Updated** ✏️
   - Triggered for general updates including:
     - Title changes
     - Description updates
     - Acceptance criteria modifications
     - Technical requirements changes
     - Scope updates
     - Issue type changes
     - Due date changes
     - Estimated hours changes

7. **Comment Added** 💬
   - Triggered when someone adds a comment to an issue
   - Shows the comment preview (truncated to 200 chars)

## Configuration

### Method 1: Bot Token (Recommended) ⭐

The Bot Token approach allows posting to multiple channels dynamically. This is the recommended method.

#### Environment Variables

Add these to your `.env` file or docker-compose:

```bash
# Slack Bot Token Configuration (Recommended)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_ENABLED=true

# Channel Configuration (customize as needed)
SLACK_DEFAULT_CHANNEL=#general
SLACK_CHANNEL_BUGS=#bugs
SLACK_CHANNEL_FEATURES=#features
SLACK_CHANNEL_TASKS=#tasks
SLACK_CHANNEL_STORIES=#features
```

#### Getting a Bot Token

1. Go to https://api.slack.com/apps
2. Create a new app or select existing
3. Navigate to **OAuth & Permissions**
4. Add the following **Bot Token Scopes**:
   - `chat:write` - Send messages
   - `chat:write.public` - Send messages to public channels
5. Click **Install to Workspace**
6. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
7. Invite the bot to channels: `/invite @YourBotName` in each channel

### Method 2: Webhook (Legacy)

If you prefer webhooks (single channel only):

```bash
# Slack Webhook Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_ENABLED=true
```

**Note:** Webhooks can only post to one channel. Use Bot Token for multi-channel support.

### Per-Project Settings

Enable Slack for specific projects:

1. Go to **Admin → Projects**
2. Edit the project
3. Enable "Slack Notifications"
4. Set the Slack channel (optional - will route based on issue type)

### Channel Routing (Bot Token Only)

With Bot Token, notifications are automatically routed to different channels:
- **Bugs** → `#bugs` channel
- **Features** → `#features` channel
- **Stories** → `#features` channel
- **Tasks** → `#tasks` channel
- **Other** → Default channel (`#general`)

You can customize these in environment variables or project settings.

## Bot vs Webhook Comparison

| Feature | Bot Token | Webhook |
|---------|-----------|---------|
| Multiple Channels | ✅ Yes | ❌ No (single channel only) |
| Dynamic Routing | ✅ Yes | ❌ No |
| Channel Override | ✅ Yes | ⚠️ Limited |
| Setup Complexity | Medium | Easy |
| Flexibility | High | Low |
| **Recommendation** | **✅ Use This** | Legacy/Fallback |

## Testing

To test notifications:

1. **Set up Bot Token** (see Configuration above)
2. **Invite bot to channels**:
   ```
   /invite @YourBotName
   ```
   Do this in each channel: #bugs, #features, #tasks, #general

3. **Enable in project settings**:
   - Go to Admin → Projects
   - Edit project
   - Enable "Slack Notifications"

4. **Test the integration**:
   - Create a test issue → Check #general (or configured default)
   - Create a bug → Check #bugs
   - Update status → Check respective channel
   - Change priority → Check respective channel
   - Add labels → Check respective channel

5. **Verify in logs**:
   ```bash
   docker logs project_manager_web | grep -i slack
   ```

## Notification Format

All notifications include:
- Direct link to the issue
- Issue key and title
- Project name
- User who made the change
- Specific change details with visual indicators

## Disabling Notifications

### Globally
Set `SLACK_ENABLED=false` in environment variables

### Per Project
Disable "Slack Notifications" in project settings

## Troubleshooting

### Not receiving notifications?

1. **Check Bot Token** is configured correctly:
   ```bash
   docker exec project_manager_web env | grep SLACK
   ```

2. **Verify bot is in channels**:
   - Go to each channel in Slack
   - Type `/invite @YourBotName`
   - Bot must be a member to post

3. **Check permissions** - Bot needs:
   - `chat:write` scope
   - `chat:write.public` scope (for public channels)

4. **Check project settings**:
   - Admin → Projects → Edit Project
   - "Slack Notifications" must be enabled

5. **Review application logs**:
   ```bash
   docker logs project_manager_web --tail 100 | grep -i slack
   ```

### Common Errors

**"channel_not_found"**
- Bot hasn't been invited to the channel
- Solution: `/invite @YourBotName` in that channel

**"not_in_channel"**
- Same as above
- Bot must be a channel member

**"invalid_auth"**
- Bot token is invalid or expired
- Solution: Regenerate token in Slack App settings

**"missing_scope"**
- Bot lacks required permissions
- Solution: Add `chat:write` and `chat:write.public` scopes, reinstall app

### Testing Bot Token Manually

Test if your bot token works:

```bash
curl -X POST https://slack.com/api/chat.postMessage \\
  -H "Authorization: Bearer xoxb-your-bot-token" \\
  -H "Content-Type: application/json" \\
  -d '{
    "channel": "#general",
    "text": "Test notification from Project Manager"
  }'
```

Expected response:
```json
{
  "ok": true,
  "channel": "C1234567890",
  "ts": "1234567890.123456",
  "message": {...}
}
```

## Notification Examples

### Status Change
```
📝 Issue Status Updated
Issue: PROJ-123
Title: Implement user authentication
Status Change: 📝 To Do → 🔄 In Progress
Updated by: john_doe
```

### Priority Change
```
⚡ Priority Changed
Issue: PROJ-123
Title: Fix critical bug
Priority Change: 🟡 Medium → 🔴 Critical
Changed by: jane_smith
```

### General Update
```
✏️ Issue Updated
Issue: PROJ-123
Title: Add payment gateway
Updated by: bob_developer
Changes:
• Title: Add stripe integration → Add payment gateway
• Due Date: 2026-02-20 → 2026-02-28
• Estimated Hours: 8h → 16h
```

## Best Practices

1. **Enable per project** - Only enable for active projects to avoid notification spam
2. **Use channels wisely** - Route bugs to #bugs for quick response
3. **Label consistently** - Label changes help team understand categorization
4. **Status updates** - Clear visibility of work progress
5. **Critical alerts** - Priority changes help team focus on urgent issues

## Advanced Configuration

### Custom Channel Mapping

Edit `services/slack_service.py`:

```python
def get_channel_for_issue_type(issue_type):
    channel_mapping = {
        'bug': '#bugs',
        'feature': '#features',
        'task': '#tasks',
        'story': '#stories',
    }
    return channel_mapping.get(issue_type, None)
```

### Notification Filtering

You can customize which events trigger notifications by modifying the conditions in `routes/issues.py`.

---

**Note**: Slack notifications require Slack workspace permissions and a valid webhook URL. Contact your Slack admin if you need help setting this up.
