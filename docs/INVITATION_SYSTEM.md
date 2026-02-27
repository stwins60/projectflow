# User Invitation System

## Overview
The user invitation system allows administrators to invite new users to join the platform via email. Invited users receive a personalized email with a registration link that is valid for 7 days.

## Features

### For Administrators

1. **Send Invitations** - Invite users by email address with a specific role
2. **Manage Invitations** - View all invitations with their status (pending, accepted, expired, cancelled)
3. **Resend Invitations** - Resend invitation emails and extend expiration for expired invitations
4. **Cancel Invitations** - Cancel pending invitations before they are accepted

### For Invited Users

1. **Email Notification** - Receive a beautifully formatted invitation email
2. **Simplified Registration** - Email address is pre-filled and verified automatically
3. **Role Assignment** - Automatically assigned the role specified in the invitation
4. **Auto-Verification** - No email verification needed for invited users

## How to Use

### Sending an Invitation

1. Log in as an administrator
2. Navigate to **Admin → Invitations**
3. Click the **"Send Invitation"** button
4. Fill in:
   - Email address of the person to invite
   - Role they should have (Developer, Project Manager, Viewer, or Admin)
5. Click **"Send Invitation"**

The invited user will receive an email with a registration link valid for 7 days.

### Accepting an Invitation

1. Open the invitation email
2. Click **"Accept Invitation & Register"**
3. Complete the registration form:
   - Email is pre-filled (cannot be changed)
   - Choose a username
   - Set a password
   - Optionally add first and last name
4. Click **"Complete Registration"**
5. Account is created and verified automatically
6. Log in with your new credentials

### Managing Invitations

The invitations page shows:

- **Total Invitations** - All invitations ever sent
- **Pending** - Invitations waiting to be accepted
- **Accepted** - Invitations that resulted in user registrations
- **Expired** - Invitations that passed their 7-day window

For each invitation, you can:

- **Resend** (⟳) - Resend the invitation email (extends expiration if expired)
- **Cancel** (×) - Cancel a pending invitation

## Invitation Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Invitation sent, waiting for user to register |
| **Accepted** | User successfully registered using the invitation |
| **Expired** | Invitation passed its 7-day validity period |
| **Cancelled** | Administrator cancelled the invitation |

## Security Features

1. **Unique Tokens** - Each invitation has a unique, secure token (32 bytes)
2. **Time-Limited** - Invitations expire after 7 days
3. **One-Time Use** - Each invitation can only be used once
4. **Admin Only** - Only administrators can send invitations
5. **Email Verified** - Invited users are auto-verified (no email confirmation needed)

## Database Schema

The invitation system adds a new `invitations` table:

```sql
CREATE TABLE invitations (
    id INTEGER PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,
    role ENUM('ADMIN', 'PROJECT_MANAGER', 'DEVELOPER', 'VIEWER'),
    status VARCHAR(20) DEFAULT 'pending',
    accepted_at DATETIME,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    invited_by_id INTEGER REFERENCES users(id)
);
```

## API Endpoints

### Admin Routes (Requires Admin Role)

- `GET /admin/invitations` - View all invitations
- `POST /admin/invitations/send` - Send a new invitation
- `POST /admin/invitations/<id>/resend` - Resend an invitation
- `POST /admin/invitations/<id>/cancel` - Cancel an invitation

### Public Routes

- `GET /auth/invite/<token>` - Accept invitation (redirects to registration)
- `GET /auth/register/invited/<token>` - Registration page for invited users
- `POST /auth/register/invited/<token>` - Process invited user registration

## Email Configuration

Invitations use the existing email service. Ensure your SMTP settings are configured:

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@example.com
```

## Customization

### Invitation Expiration

To change the default 7-day expiration, edit `models.py`:

```python
# In the Invitation.__init__ method
if not self.expires_at:
    # Change timedelta(days=7) to your preferred duration
    self.expires_at = datetime.utcnow() + timedelta(days=14)  # 14 days
```

### Email Template

The invitation email template is in `services/email_service.py` in the `send_invitation_email()` function. Customize the HTML and text content as needed.

### Default Role

To change the default role for invitations, edit the form in `templates/admin/invitations.html`:

```html
<select class="form-select" id="role" name="role" required>
    <option value="developer" selected>Developer</option>  <!-- Change 'selected' -->
    <option value="project_manager">Project Manager</option>
    <option value="viewer">Viewer</option>
    <option value="admin">Admin</option>
</select>
```

## Troubleshooting

### Invitation Email Not Sent

1. Check SMTP configuration in settings or `.env` file
2. Check application logs for email errors
3. Verify MAIL_SERVER is accessible from the container
4. Test email with a simple message first

### "Invalid or expired invitation" Error

1. Check if invitation has passed expiration date
2. Verify the token in the URL matches the database
3. Check if invitation status is 'pending'
4. Ensure invitation wasn't cancelled

### User Already Exists

- The system prevents sending invitations to email addresses that already have accounts
- Check the Users page to see if the email is already registered

## Migration

The invitation feature adds a new database table. To apply the migration:

```bash
docker compose exec web flask db upgrade
```

If you need to rollback:

```bash
docker compose exec web flask db downgrade
```

## Future Enhancements

Potential improvements for the invitation system:

1. **Bulk Invitations** - Upload CSV to invite multiple users at once
2. **Custom Messages** - Add personal message to invitation emails
3. **Project Assignment** - Automatically add invited users to specific projects
4. **Invitation Templates** - Pre-defined role+message templates
5. **Usage Analytics** - Track invitation acceptance rates
6. **Reminders** - Automatically remind users about pending invitations

---

**Need Help?** Contact your system administrator or refer to the main documentation.
