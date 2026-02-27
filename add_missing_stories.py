#!/usr/bin/env python3
"""
Add missing story tickets from JIRA_TICKETS.md
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Issue, IssueType, IssuePriority, IssueStatus, Project, Sprint, Epic, User

def main():
    """Add missing story issues."""
    
    with app.app_context():
        # Get project and epic
        project = Project.query.filter_by(key='ARA').first()
        epic = Epic.query.filter_by(project_id=project.id).first()
        user = User.query.first()
        
        # Get sprints
        sprints = {s.name: s for s in Sprint.query.filter_by(project_id=project.id).all()}
        
        # Define missing stories
        stories = [
            {
                'title': 'CI/CD Pipeline with GitHub Actions',
                'priority': IssuePriority.HIGH,
                'story_points': 13,
                'sprint': 'Sprint 1',
                'description': 'As a Developer, I want an automated CI/CD pipeline using GitHub Actions to automatically test, build, and deploy the application when code is pushed to the repository.',
                'acceptance_criteria': '''- [ ] Automated linting and code quality checks on pull requests
- [ ] Automated unit and integration tests
- [ ] Automated Docker image builds on merge to main
- [ ] Push images to Docker Hub/GitHub Container Registry
- [ ] Automated deployment to staging environment
- [ ] Manual approval for production deployment
- [ ] Rollback capability
- [ ] Slack/Discord notifications for build status''',
                'technical_requirements': '''**Pipeline Stages:**
1. Lint & Code Quality (flake8, pylint, bandit)
2. Test (unit, integration, coverage report)
3. Build Docker image
4. Security scan with Trivy
5. Push to container registry
6. Deploy to staging
7. Deploy to production with approval'''
            },
            {
                'title': 'Alternative CI/CD with Jenkins',
                'priority': IssuePriority.MEDIUM,
                'story_points': 13,
                'sprint': 'Sprint 2',
                'description': 'As a DevOps Engineer, I want to implement a Jenkins-based CI/CD pipeline as an alternative/complement to GitHub Actions for organizations preferring self-hosted CI/CD.',
                'acceptance_criteria': '''- [ ] Jenkins server setup with Docker
- [ ] Multibranch pipeline configuration
- [ ] Automated builds on git push/PR
- [ ] Integration with GitHub webhooks
- [ ] Blue Ocean plugin for better UI
- [ ] Automated testing and deployment
- [ ] Build artifacts archival
- [ ] Email/Slack notifications'''
            },
            {
                'title': 'Monitoring & Observability Stack',
                'priority': IssuePriority.HIGH,
                'story_points': 13,
                'sprint': 'Sprint 2',
                'description': 'As an Operations Engineer, I want comprehensive monitoring and observability to proactively detect issues, track performance metrics, and ensure system reliability.',
                'acceptance_criteria': '''- [ ] Prometheus for metrics collection
- [ ] Grafana dashboards for visualization
- [ ] Application metrics (requests, latency, errors)
- [ ] Infrastructure metrics (CPU, memory, disk, network)
- [ ] Log aggregation with Loki or ELK
- [ ] Alerting rules for critical metrics
- [ ] Custom dashboards for business metrics
- [ ] 7-day metric retention minimum'''
            },
            {
                'title': 'Logging & Log Aggregation',
                'priority': IssuePriority.MEDIUM,
                'story_points': 8,
                'sprint': 'Sprint 3',
                'description': 'As a Developer, I want centralized log aggregation and analysis to quickly debug issues and track application behavior across all services.',
                'acceptance_criteria': '''- [ ] Structured JSON logging
- [ ] Log levels properly configured
- [ ] Centralized log collection (Loki/ELK)
- [ ] Log retention policy (30 days)
- [ ] Searchable logs in Grafana/Kibana
- [ ] Correlation IDs for request tracing
- [ ] Sensitive data redaction
- [ ] Log-based alerts'''
            },
            {
                'title': 'Security Scanning & Compliance',
                'priority': IssuePriority.HIGH,
                'story_points': 8,
                'sprint': 'Sprint 3',
                'description': 'As a Security Engineer, I want automated security scanning in the CI/CD pipeline to identify vulnerabilities early and maintain compliance standards.',
                'acceptance_criteria': '''- [ ] Dependency vulnerability scanning (Snyk/Dependabot)
- [ ] Docker image scanning (Trivy)
- [ ] SAST (Static Application Security Testing)
- [ ] Secret detection in code
- [ ] License compliance checking
- [ ] Security scan reports in CI
- [ ] Block deployment if critical vulnerabilities found
- [ ] Automated security patch PRs'''
            },
            {
                'title': 'Infrastructure Automation with Ansible',
                'priority': IssuePriority.MEDIUM,
                'story_points': 13,
                'sprint': 'Sprint 4',
                'description': 'As a DevOps Engineer, I want to automate on-premises Ubuntu server configuration using Ansible to ensure consistent, reproducible, and version-controlled infrastructure setup.',
                'acceptance_criteria': '''- [ ] Ansible playbooks for server provisioning
- [ ] Docker and Docker Compose installation
- [ ] PostgreSQL database setup and hardening
- [ ] UFW firewall configuration
- [ ] SSL certificate management (Let\'s Encrypt)
- [ ] System user and permission management
- [ ] Automated security updates
- [ ] Environment separation (dev/staging/prod)
- [ ] Cloudflare Tunnel configuration
- [ ] Backup cron jobs setup'''
            },
            {
                'title': 'Database Backup & Disaster Recovery',
                'priority': IssuePriority.HIGH,
                'story_points': 8,
                'sprint': 'Sprint 4',
                'description': 'As an Operations Engineer, I want automated database backups and a disaster recovery plan to prevent data loss and ensure business continuity.',
                'acceptance_criteria': '''- [ ] Daily automated database backups
- [ ] Backup retention policy (30 days local, 90 days offsite)
- [ ] Encrypted backups stored locally and offsite
- [ ] Automated backup verification
- [ ] Point-in-time recovery capability
- [ ] Documented recovery procedures
- [ ] Regular recovery drills
- [ ] Backup monitoring and alerts'''
            },
            {
                'title': 'Performance Testing & Load Testing',
                'priority': IssuePriority.MEDIUM,
                'story_points': 8,
                'sprint': 'Sprint 5',
                'description': 'As a Performance Engineer, I want automated performance and load testing to ensure the application can handle expected traffic and identify bottlenecks.',
                'acceptance_criteria': '''- [ ] Locust/JMeter load testing setup
- [ ] Performance benchmarks documented
- [ ] Load test scenarios for critical paths
- [ ] Automated performance tests in CI
- [ ] Performance regression detection
- [ ] Stress testing for peak loads
- [ ] Database query optimization
- [ ] API response time targets met'''
            }
        ]
        
        print("=" * 80)
        print("ADDING MISSING STORY TICKETS")
        print("=" * 80)
        
        for story_data in stories:
            # Check if story exists
            existing = Issue.query.filter_by(
                project_id=project.id,
                title=story_data['title']
            ).first()
            
            if existing:
                print(f"  ⊙ Skipping: {story_data['title']} (already exists)")
                continue
            
            # Get sprint
            sprint = sprints.get(story_data['sprint'])
            
            # Create issue
            issue = Issue(
                project_id=project.id,
                number=project.generate_issue_number(),
                title=story_data['title'],
                description=story_data['description'],
                acceptance_criteria=story_data['acceptance_criteria'],
                technical_requirements=story_data.get('technical_requirements', ''),
                status=IssueStatus.BACKLOG,
                priority=story_data['priority'],
                issue_type=IssueType.STORY,
                story_points=story_data['story_points'],
                reporter_id=user.id,
                epic_id=epic.id,
                sprint_id=sprint.id if sprint else None
            )
            
            db.session.add(issue)
            print(f"  ✓ Created: {story_data['title']} (Sprint: {story_data['sprint']})")
        
        db.session.commit()
        
        print("\n" + "=" * 80)
        print("COMPLETE!")
        print("=" * 80)
        print(f"Total issues in project: {project.issue_count}")
        print("=" * 80)

if __name__ == '__main__':
    main()
