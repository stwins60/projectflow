#!/usr/bin/env python3
"""
Script to import Jira tickets from JIRA_TICKETS.md into the database.
Creates project, epic, and all stories/tasks from the markdown file.
"""
import sys
import os
import re
from datetime import datetime, date

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    Project, Epic, Issue, IssueType, IssuePriority, IssueStatus,
    User, Sprint, Version
)


def parse_jira_tickets_md():
    """Parse the JIRA_TICKETS.md file and extract ticket information."""
    
    with open('JIRA_TICKETS.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tickets = []
    
    # Split content by story markers to handle each story section
    # Look for patterns like: ## 🚀 STORY 1: Title or ## 🔄 STORY 2: Title  
    story_sections = re.split(r'(?=## [🚀🔄📊📝🔒🏗️🔄📈🚀] STORY \d+:)', content)
    
    for section in story_sections[1:]:  # Skip first empty section
        lines = section.split('\n')
        
        # Extract ticket ID
        ticket_match = re.search(r'\*\*Ticket\*\*:\s*(ARA-\d+)', section)
        if not ticket_match:
            continue
        ticket_id = ticket_match.group(1)
        
        # Extract title
        title_match = re.search(r'## [🚀🔄📊📝🔒🏗️🔄📈🚀] STORY \d+: (.+?)(?:\n|$)', section)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        
        # Extract type, priority, story points, sprint
        type_match = re.search(r'\*\*Type\*\*:\s*(\w+)', section)
        priority_match = re.search(r'\*\*Priority\*\*:\s*(\w+)', section)
        points_match = re.search(r'\*\*Story Points\*\*:\s*(\d+)', section)
        sprint_match = re.search(r'\*\*Sprint\*\*:\s*(.+?)(?:\n|$)', section)
        
        issue_type = type_match.group(1).lower() if type_match else 'story'
        priority = priority_match.group(1).lower() if priority_match else 'medium'
        story_points = int(points_match.group(1)) if points_match else 5
        sprint = sprint_match.group(1).strip() if sprint_match else 'Backlog'
        
        # Extract description
        desc_match = re.search(r'### Description\n(.+?)(?=\n\n###|\n---|\Z)', section, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""
        
        # Extract acceptance criteria
        ac_match = re.search(r'### Acceptance Criteria\n(.+?)(?=\n\n###|\n---|\Z)', section, re.DOTALL)
        acceptance_criteria = ac_match.group(1).strip() if ac_match else ""
        
        # Extract technical details
        tech_match = re.search(r'### Technical Details\n(.+?)(?=\n\n###|\n---|\Z)', section, re.DOTALL)
        technical_requirements = tech_match.group(1).strip() if tech_match else ""
        
        # Extract implementation tasks
        impl_match = re.search(r'### Implementation Tasks\n(.+?)(?=\n\n###|\n---|\Z)', section, re.DOTALL)
        implementation_tasks = impl_match.group(1).strip() if impl_match else ""
        
        tickets.append({
            'ticket_id': ticket_id,
            'title': title,
            'description': description,
            'acceptance_criteria': acceptance_criteria,
            'technical_requirements': technical_requirements,
            'implementation_tasks': implementation_tasks,
            'issue_type': 'story',
            'priority': priority,
            'story_points': story_points,
            'sprint': sprint,
        })
    
    # Parse TASK tickets
    task_pattern = r'### (TASK-\d+): (.+?)\n- \*\*Parent\*\*: (.+?)\s+\n- \*\*Points\*\*: (\d+)\s+\n(.+?)(?=\n\n###|---|\Z)'
    
    for match in re.finditer(task_pattern, content, re.DOTALL):
        ticket_id, title, parent, points, description = match.groups()
        
        tickets.append({
            'ticket_id': ticket_id,
            'title': title.strip(),
            'description': description.strip(),
            'acceptance_criteria': '',
            'technical_requirements': '',
            'implementation_tasks': '',
            'issue_type': 'task',
            'priority': 'medium',
            'story_points': int(points),
            'sprint': 'Backlog',
        })
    
    # Parse DOC tickets
    doc_pattern = r'### (DOC-\d+): (.+?)\n- \*\*Points\*\*: (\d+)\s+\n(.+?)(?=\n\n###|---|\Z)'
    
    for match in re.finditer(doc_pattern, content, re.DOTALL):
        ticket_id, title, points, description = match.groups()
        
        tickets.append({
            'ticket_id': ticket_id,
            'title': title.strip(),
            'description': description.strip(),
            'acceptance_criteria': '',
            'technical_requirements': '',
            'implementation_tasks': '',
            'issue_type': 'task',
            'priority': 'low',
            'story_points': int(points),
            'sprint': 'Backlog',
        })
    
    # Parse BUG tickets
    bug_pattern = r'### (BUG-\d+): (.+?)\n- \*\*Priority\*\*: (\w+)\s+\n- \*\*Points\*\*: (\d+)\s+\n(.+?)(?=\n\n###|---|\Z)'
    
    for match in re.finditer(bug_pattern, content, re.DOTALL):
        ticket_id, title, priority, points, description = match.groups()
        
        tickets.append({
            'ticket_id': ticket_id,
            'title': title.strip(),
            'description': description.strip(),
            'acceptance_criteria': '',
            'technical_requirements': '',
            'implementation_tasks': '',
            'issue_type': 'bug',
            'priority': priority.lower(),
            'story_points': int(points),
            'sprint': 'Backlog',
        })
    
    # Parse IMPROVEMENT tickets
    imp_pattern = r'### (IMPROVEMENT-\d+): (.+?)\n- \*\*Priority\*\*: (\w+)\s+\n- \*\*Points\*\*: (\d+)\s+\n(.+?)(?=\n\n###|---|\Z)'
    
    for match in re.finditer(imp_pattern, content, re.DOTALL):
        ticket_id, title, priority, points, description = match.groups()
        
        tickets.append({
            'ticket_id': ticket_id,
            'title': title.strip(),
            'description': description.strip(),
            'acceptance_criteria': '',
            'technical_requirements': '',
            'implementation_tasks': '',
            'issue_type': 'feature',
            'priority': priority.lower(),
            'story_points': int(points),
            'sprint': 'Backlog',
        })
    
    return tickets


def create_sprints(project):
    """Create the sprints mentioned in the tickets."""
    sprints_data = [
        {'name': 'Sprint 1', 'start': date(2026, 3, 1), 'end': date(2026, 3, 14)},
        {'name': 'Sprint 2', 'start': date(2026, 3, 15), 'end': date(2026, 3, 28)},
        {'name': 'Sprint 3', 'start': date(2026, 3, 29), 'end': date(2026, 4, 11)},
        {'name': 'Sprint 4', 'start': date(2026, 4, 12), 'end': date(2026, 4, 25)},
        {'name': 'Sprint 5', 'start': date(2026, 4, 26), 'end': date(2026, 5, 9)},
    ]
    
    sprints = {}
    for sprint_data in sprints_data:
        sprint = Sprint.query.filter_by(
            project_id=project.id,
            name=sprint_data['name']
        ).first()
        
        if not sprint:
            sprint = Sprint(
                name=sprint_data['name'],
                goal=f"DevOps Infrastructure for AI Resume Analyzer",
                start_date=sprint_data['start'],
                end_date=sprint_data['end'],
                project_id=project.id
            )
            db.session.add(sprint)
            db.session.flush()
        
        sprints[sprint_data['name']] = sprint
    
    return sprints


def get_sprint_from_text(sprint_text, sprints):
    """Get sprint object from text like 'Sprint 1' or 'Sprint 1-2'."""
    if not sprint_text or sprint_text == 'Backlog':
        return None
    
    # Extract first sprint number
    match = re.search(r'Sprint (\d+)', sprint_text)
    if match:
        sprint_name = f"Sprint {match.group(1)}"
        return sprints.get(sprint_name)
    
    return None


def main():
    """Main function to import all Jira tickets."""
    
    print("=" * 80)
    print("JIRA TICKET IMPORT SCRIPT")
    print("=" * 80)
    
    with app.app_context():
        # Get the first user (admin) to be the owner/reporter
        from models import UserRole
        user = User.query.filter_by(role=UserRole.ADMIN).first()
        if not user:
            user = User.query.first()
        
        if not user:
            print("❌ Error: No users found. Please create a user first.")
            return
        
        print(f"✓ Using user: {user.username} (ID: {user.id})")
        
        # Create or get the project
        project = Project.query.filter_by(key='ARA').first()
        
        if not project:
            print("\n📦 Creating project: AI Resume Analyzer (ARA)")
            project = Project(
                name='AI Resume Analyzer',
                key='ARA',
                description='DevOps Infrastructure & Automation for AI Resume Analyzer application',
                color='#6366f1',
                is_active=True,
                is_public=False,
                owner_id=user.id
            )
            db.session.add(project)
            db.session.flush()
            print(f"✓ Project created (ID: {project.id})")
        else:
            print(f"\n✓ Project already exists (ID: {project.id})")
        
        # Create the Epic
        epic = Epic.query.filter_by(
            project_id=project.id,
            name='DevOps Infrastructure & Automation'
        ).first()
        
        if not epic:
            print("\n🎯 Creating Epic: EPIC-1 - DevOps Infrastructure & Automation")
            epic = Epic(
                name='DevOps Infrastructure & Automation',
                description=(
                    'Implement comprehensive DevOps practices including containerization improvements, '
                    'CI/CD pipelines, monitoring, security scanning, and infrastructure automation '
                    'for the AI Resume Analyzer application.\n\n'
                    'Business Value: Improve deployment reliability, reduce manual errors, enable '
                    'faster releases, and ensure system health through automated monitoring and alerts.\n\n'
                    'Timeline: 4-6 weeks'
                ),
                color='#8b5cf6',
                status='open',
                project_id=project.id,
                owner_id=user.id
            )
            db.session.add(epic)
            db.session.flush()
            print(f"✓ Epic created (ID: {epic.id})")
        else:
            print(f"\n✓ Epic already exists (ID: {epic.id})")
        
        # Create sprints
        print("\n📅 Creating sprints...")
        sprints = create_sprints(project)
        print(f"✓ Created/verified {len(sprints)} sprints")
        
        # Parse tickets from markdown file
        print("\n📄 Parsing JIRA_TICKETS.md...")
        tickets = parse_jira_tickets_md()
        print(f"✓ Found {len(tickets)} tickets to import")
        
        # Create issues
        print("\n🎫 Creating issues...")
        created_count = 0
        skipped_count = 0
        
        for ticket_data in tickets:
            # Check if issue already exists with this title
            existing = Issue.query.filter_by(
                project_id=project.id,
                title=ticket_data['title']
            ).first()
            
            if existing:
                print(f"  ⊙ Skipping {ticket_data['ticket_id']}: {ticket_data['title'][:50]}... (already exists)")
                skipped_count += 1
                continue
            
            # Map priority
            priority_map = {
                'low': IssuePriority.LOW,
                'medium': IssuePriority.MEDIUM,
                'high': IssuePriority.HIGH,
                'critical': IssuePriority.CRITICAL
            }
            priority = priority_map.get(ticket_data['priority'], IssuePriority.MEDIUM)
            
            # Map issue type
            type_map = {
                'story': IssueType.STORY,
                'task': IssueType.TASK,
                'bug': IssueType.BUG,
                'feature': IssueType.FEATURE,
            }
            issue_type = type_map.get(ticket_data['issue_type'], IssueType.TASK)
            
            # Combine description with implementation tasks
            full_description = ticket_data['description']
            if ticket_data['implementation_tasks']:
                full_description += f"\n\n### Implementation Tasks\n{ticket_data['implementation_tasks']}"
            
            # Get sprint
            sprint = get_sprint_from_text(ticket_data['sprint'], sprints)
            
            # Create the issue
            issue = Issue(
                project_id=project.id,
                number=project.generate_issue_number(),
                title=ticket_data['title'],
                description=full_description,
                acceptance_criteria=ticket_data['acceptance_criteria'],
                technical_requirements=ticket_data['technical_requirements'],
                status=IssueStatus.BACKLOG,
                priority=priority,
                issue_type=issue_type,
                story_points=ticket_data.get('story_points'),
                reporter_id=user.id,
                epic_id=epic.id,
                sprint_id=sprint.id if sprint else None
            )
            
            db.session.add(issue)
            print(f"  ✓ Created {ticket_data['ticket_id']}: {ticket_data['title'][:60]}...")
            created_count += 1
        
        # Commit all changes
        print("\n💾 Committing changes to database...")
        db.session.commit()
        
        print("\n" + "=" * 80)
        print("IMPORT COMPLETE!")
        print("=" * 80)
        print(f"Project: {project.name} ({project.key})")
        print(f"Epic: {epic.name}")
        print(f"Sprints created: {len(sprints)}")
        print(f"Issues created: {created_count}")
        print(f"Issues skipped: {skipped_count}")
        print(f"Total issues in project: {project.issue_count}")
        print("=" * 80)


if __name__ == '__main__':
    main()
