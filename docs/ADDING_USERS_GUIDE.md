# 👥 How to Add Users to Organizations

## 📍 Quick Reference

**You have 3 ways to add users to your organization:**

1. **Invite via Email** (Recommended) - User gets email, registers, and automatically joins
2. **Admin Panel** (For existing users) - Manually add existing users
3. **Database** (Emergency/Bulk) - Direct SQL commands

---

## 🎯 Method 1: Invite New Users via Email (Recommended)

This is the **best method** for adding new team members who don't have accounts yet.

### Steps:

1. **Navigate to Admin Panel:**
   - Log in as an Admin or Organization Owner
   - Click on **"Admin"** in the navigation menu
   - Select **"Invitations"**

2. **Send Invitation:**
   - Click **"Send Invitation"** button
   - Fill in the form:
     - **Email**: User's email address
     - **Role**: Choose from:
       - `Developer` - Can create/edit issues and comments
       - `Project Manager` - Can create projects and manage teams
       - `Viewer` - Read-only access
       - `Admin` - Full access to organization
   - Click **"Send Invitation"**

3. **User Receives Email:**
   - Invitation is valid for **7 days**
   - Email contains registration link
   - User clicks link and completes registration
   - Account is automatically verified and added to your organization

### Invitation Management:

- **View Status**: See all invitations (pending, accepted, expired)
- **Resend**: Extend expiration and resend email
- **Cancel**: Cancel pending invitations

**Location**: Admin → Invitations → Send Invitation

---

## 🔧 Method 2: Add Existing Users (Admin Panel)

Use this when users **already have accounts** but need to join your organization.

### Current Implementation:

⚠️ **Note**: The UI for adding existing users to organizations is available in the Admin panel.

### Manual Alternative (Until UI is complete):

If you need to add existing users manually, use Method 3 below.

---

## 💻 Method 3: Database Method (Direct SQL)

Use this for **bulk operations** or **emergency access**.

### Prerequisites:
- Access to the server
- Docker compose running

### Steps:

1. **Connect to database:**
```bash
cd /home/prod-server-2/Development/plane-selfhost/project_manager
docker compose exec db psql -U projectmgr -d projectmanager
```

2. **Find the organization ID:**
```sql
-- List all organizations
SELECT id, name, slug FROM organizations;
```

3. **Find the user ID:**
```sql
-- List all users
SELECT id, username, email FROM users;
```

4. **Add user to organization:**
```sql
BEGIN;

-- Add user to organization_members table
INSERT INTO organization_members (user_id, organization_id, role) 
VALUES (USER_ID, ORG_ID, 'member')
ON CONFLICT DO NOTHING;

-- Set user's current organization
UPDATE users 
SET current_organization_id = ORG_ID 
WHERE id = USER_ID;

COMMIT;
```

### Example (Adding user to Default Organization):

```sql
-- Add user with ID 5 to organization with ID 1 as a member
BEGIN;

INSERT INTO organization_members (user_id, organization_id, role) 
VALUES (5, 1, 'member')
ON CONFLICT DO NOTHING;

UPDATE users SET current_organization_id = 1 WHERE id = 5;

COMMIT;
```

### Verify:
```sql
-- Check organization members
SELECT u.id, u.username, u.email, om.role 
FROM users u 
JOIN organization_members om ON u.id = om.user_id 
WHERE om.organization_id = 1 
ORDER BY u.id;
```

---

## 🎭 User Roles Explained

| Role | Permissions |
|------|-------------|
| **Owner** | Created the organization, full access |
| **Admin** | Full organization access, manage users |
| **Project Manager** | Create projects, manage project members |
| **Developer** | Create/edit issues, comments, update status |
| **Viewer** | Read-only access to projects and issues |

**Setting Roles:**
- During invitation: Select role in invitation form
- Database method: Use `'owner'`, `'admin'`, `'member'` in the role column

---

## 🔍 Common Tasks

### Check who's in an organization:
```bash
docker compose exec db psql -U projectmgr -d projectmanager -c "
SELECT u.id, u.username, u.email, om.role, o.name as organization
FROM users u 
JOIN organization_members om ON u.id = om.user_id 
JOIN organizations o ON om.organization_id = o.id
ORDER BY o.name, u.username;
"
```

### Remove user from organization:
```bash
docker compose exec db psql -U projectmgr -d projectmanager -c "
DELETE FROM organization_members 
WHERE user_id = USER_ID AND organization_id = ORG_ID;
"
```

### Change user's role:
```bash
docker compose exec db psql -U projectmgr -d projectmanager -c "
UPDATE organization_members 
SET role = 'admin' 
WHERE user_id = USER_ID AND organization_id = ORG_ID;
"
```

### Switch user's active organization:
```bash
docker compose exec db psql -U projectmgr -d projectmanager -c "
UPDATE users 
SET current_organization_id = NEW_ORG_ID 
WHERE id = USER_ID;
"
```

---

## 🆘 Troubleshooting

### User can't see organization projects

**Check if user is in organization:**
```sql
SELECT * FROM organization_members 
WHERE user_id = USER_ID AND organization_id = ORG_ID;
```

**Check user's current organization:**
```sql
SELECT id, username, current_organization_id 
FROM users WHERE id = USER_ID;
```

### Invitation email not received

1. Check SMTP settings in `.env`:
   ```env
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

2. Check spam folder

3. Verify email in invitations table:
   ```sql
   SELECT * FROM invitations WHERE email = 'user@example.com';
   ```

4. Resend invitation from Admin panel

### User seeing wrong organization's data

**Fix:**
```sql
-- Set user to correct organization
UPDATE users 
SET current_organization_id = CORRECT_ORG_ID 
WHERE id = USER_ID;
```

Then have the user log out and log back in.

---

## 📚 Related Documentation

- [INVITATION_SYSTEM.md](INVITATION_SYSTEM.md) - Detailed invitation system documentation
- [SAAS_FEATURES.md](SAAS_FEATURES.md) - Multi-tenancy architecture
- [README.md](README.md) - Full application documentation

---

## 🎯 Best Practices

1. **Use Email Invitations** - Cleanest way to onboard new users
2. **Verify Organization Context** - Always check current_organization_id
3. **Use Appropriate Roles** - Start with lower permissions, upgrade as needed
4. **Document Manual Changes** - Keep notes when using database method
5. **Regular Audits** - Periodically review organization members

---

**Need Help?** Check the logs: `docker compose logs web -f`
