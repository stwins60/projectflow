# Multi-Tenant SaaS Project Manager

This project manager has been enhanced with multi-tenant SaaS capabilities, allowing multiple organizations to use the platform independently.

## 🚀 Key Features

### Multi-Tenancy
- **Organizations**: Each customer gets their own isolated workspace
- **Data Isolation**: Projects, issues, and wiki pages are scoped to organizations
- **Subdomain Support**: Each organization can have their own subdomain (e.g., acme.projectmanager.app)
- **Custom Branding**: Organizations can customize colors and logos

### Self-Service Signup
- **Easy Onboarding**: New customers can sign up and create their workspace in minutes
- **14-Day Free Trial**: Automatic trial period for new organizations
- **No Credit Card Required**: Start using immediately without payment information

### Subscription Management
- **Multiple Plans**: Free, Starter, Professional, Enterprise
- **Usage Limits**: Control users, projects, and storage per plan
- **Flexible Billing**: Manage subscriptions and upgrades
- **Trial Management**: Automatic trial expiration handling

### Organization Features
- **Member Management**: Invite and manage team members
- **Role-Based Access**: Owner, Admin, Member roles
- **Settings**: Customize organization details and preferences
- **Usage Tracking**: Monitor users, projects, and storage usage

## 📋 Subscription Plans

### Free Plan
- 5 users
- 3 projects
- 100 MB storage
- Basic features

### Starter Plan - $29/month
- 10 users
- 10 projects
- 1 GB storage
- GitHub & Slack integration
- Custom branding

### Professional Plan - $79/month
- 50 users
- 50 projects
- 10 GB storage
- Advanced reporting
- API access
- Priority support

### Enterprise Plan - $199/month
- Unlimited users
- Unlimited projects
- 100 GB storage
- Custom domain
- SSO
- Dedicated support
- SLA

## 🎯 Getting Started

### For New Customers

1. **Sign Up**
   - Visit `http://localhost:5987/org/signup`
   - Enter organization name and subdomain
   - Create admin account
   - Start 14-day free trial automatically

2. **Set Up Workspace**
   - Add team members via Organization → Members
   - Create your first project
   - Configure integrations (GitHub, Slack)
   - Customize branding in settings

3. **Upgrade When Ready**
   - Visit Organization → Billing
   - Choose a plan that fits your needs
   - Enter payment information
   - Continue seamlessly after trial

### For Platform Administrators

1. **Super Admin Access**
   - Set `is_super_admin = true` for admin users in database
   - Access all organizations and settings
   - Monitor platform usage and health

2. **Manage Organizations**
   - View all organizations
   - Suspend or activate accounts
   - Adjust limits and quotas
   - Handle billing issues

## 🔧 Technical Architecture

### Database Structure

**organizations** table:
- Core tenant data
- Subscription details
- Limits and quotas
- Billing information

**organization_members** table:
- User-organization relationships
- Role assignments
- Join timestamps

**Updated Models**:
- `users`: Added `current_organization_id` and `is_super_admin`
- `projects`: Added `organization_id` with composite unique constraint
- All data is now scoped to organizations

### Multi-Tenancy Implementation

1. **Organization Context**
   - `current_organization_id` tracks active workspace per user
   - Context processor injects organization into all templates
   - Middleware checks organization status on each request

2. **Data Isolation**
   - All queries filtered by organization_id
   - Projects scoped to organization
   - Users can belong to multiple organizations
   - Switch between organizations without re-login

3. **Access Control**
   - Organization-level roles (Owner, Admin, Member)
   - Project-level permissions maintained
   - Super admins can access all organizations

## 🛠️ Migration Guide

### Upgrading Existing Installation

```bash
# Apply migrations
docker compose exec -T web flask db upgrade

# Verify migration
docker compose exec -T db psql -U projectmgr -d projectmanager -c "SELECT * FROM organizations;"
```

### What Happens During Migration

1. Creates `organizations` and `organization_members` tables
2. Adds `current_organization_id` to `users` table
3. Adds `organization_id` to `projects` table
4. Creates a "Default Organization" for existing data
5. Assigns all existing users to default organization as owners
6. Updates project key constraint to be unique per organization

## 🔐 Security Considerations

- All data is isolated by organization_id
- Users can only access their organization's data
- Super admins have platform-wide access
- Trial status enforced before each request
- Suspended accounts blocked from access

## 📊 Usage Monitoring

Organizations can track:
- Current user count vs limit
- Project count vs limit
- Storage usage vs limit
- Trial days remaining
- Subscription status

## 🎨 Customization Options

Each organization can customize:
- Organization name and contact details
- Primary brand color
- Logo upload (ready for implementation)
- Custom domain (ready for implementation)
- Settings stored in JSONB field

## 🔄 Switching Organizations

Users can:
1. Be members of multiple organizations
2. Switch between organizations via dropdown
3. See all their organizations in user menu
4. Have different roles in different organizations

## 📝 Next Steps

Future enhancements ready for implementation:
- [ ] Payment gateway integration (Stripe/PayPal)
- [ ] Email invitation system
- [ ] Custom domain support
- [ ] Logo upload functionality
- [ ] Usage analytics dashboards
- [ ] API rate limiting per plan
- [ ] White-label options for enterprise
- [ ] SSO integration (SAML, OAuth)

## 🆘 Support

For issues or questions:
1. Check organization settings
2. Verify subscription status
3. Contact super admin
4. Review platform logs

## 📚 API Endpoints

### Organization Routes
- `GET /org/signup` - Organization signup page
- `POST /org/signup` - Create new organization
- `GET /org/settings` - Organization settings
- `POST /org/settings/update` - Update settings
- `GET /org/members` - Manage members
- `POST /org/members/invite` - Invite member
- `GET /org/switch/<id>` - Switch organization
- `GET /org/billing` - Billing and plans

### Root Route
- `/` - Redirects to signup for new users, dashboard for authenticated

## 🎉 Success!

Your project manager is now a fully-featured multi-tenant SaaS application ready to onboard customers!
