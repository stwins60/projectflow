"""
Wiki routes for project documentation.
Provides Confluence-like features for creating and managing documentation.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import WikiPage, Project, User
import re
from datetime import datetime

wiki_bp = Blueprint('wiki', __name__)


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


@wiki_bp.route('/projects/<int:project_id>/wiki')
@login_required
def index(project_id):
    """List all wiki pages for a project."""
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    # Get root pages (pages without parent)
    root_pages = WikiPage.query.filter_by(
        project_id=project_id,
        parent_id=None,
        is_active=True
    ).order_by(WikiPage.order, WikiPage.title).all()
    
    # Get all pages for search/listing
    all_pages = WikiPage.query.filter_by(
        project_id=project_id,
        is_active=True
    ).order_by(WikiPage.title).all()
    
    return render_template('wiki/index.html',
                         project=project,
                         root_pages=root_pages,
                         all_pages=all_pages)


@wiki_bp.route('/projects/<int:project_id>/wiki/<int:page_id>')
@login_required
def view(project_id, page_id):
    """View a single wiki page."""
    project = Project.query.get_or_404(project_id)
    page = WikiPage.query.filter_by(id=page_id, project_id=project_id).first_or_404()
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    return render_template('wiki/view.html',
                         project=project,
                         page=page)


@wiki_bp.route('/projects/<int:project_id>/wiki/new', methods=['GET', 'POST'])
@login_required
def create(project_id):
    """Create a new wiki page."""
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        parent_id = request.form.get('parent_id', type=int)
        
        if not title:
            flash('Page title is required.', 'danger')
            return redirect(url_for('wiki.create', project_id=project_id))
        
        # Generate slug
        slug = slugify(title)
        
        # Check for duplicate slug in project
        existing = WikiPage.query.filter_by(
            project_id=project_id,
            slug=slug,
            is_active=True
        ).first()
        
        if existing:
            # Add number to make it unique
            counter = 1
            new_slug = f"{slug}-{counter}"
            while WikiPage.query.filter_by(project_id=project_id, slug=new_slug, is_active=True).first():
                counter += 1
                new_slug = f"{slug}-{counter}"
            slug = new_slug
        
        # Create page
        page = WikiPage(
            title=title,
            slug=slug,
            content=content,
            project_id=project_id,
            parent_id=parent_id,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        
        db.session.add(page)
        db.session.commit()
        
        flash(f'Wiki page "{title}" created successfully!', 'success')
        return redirect(url_for('wiki.view', project_id=project_id, page_id=page.id))
    
    # GET request - show form
    # Get all pages for parent selection
    all_pages = WikiPage.query.filter_by(
        project_id=project_id,
        is_active=True
    ).order_by(WikiPage.title).all()
    
    parent_id = request.args.get('parent_id', type=int)
    
    return render_template('wiki/edit.html',
                         project=project,
                         page=None,
                         all_pages=all_pages,
                         parent_id=parent_id)


@wiki_bp.route('/projects/<int:project_id>/wiki/<int:page_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_id, page_id):
    """Edit an existing wiki page."""
    project = Project.query.get_or_404(project_id)
    page = WikiPage.query.filter_by(id=page_id, project_id=project_id).first_or_404()
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        parent_id = request.form.get('parent_id', type=int)
        
        if not title:
            flash('Page title is required.', 'danger')
            return redirect(url_for('wiki.edit', project_id=project_id, page_id=page_id))
        
        # Check if parent would create circular reference
        if parent_id:
            parent = WikiPage.query.get(parent_id)
            if parent:
                # Check if the chosen parent is a descendant of this page
                descendants = page.get_all_descendants()
                if parent in descendants or parent.id == page.id:
                    flash('Cannot set parent - would create circular reference.', 'danger')
                    return redirect(url_for('wiki.edit', project_id=project_id, page_id=page_id))
        
        # Update page
        page.title = title
        page.content = content
        page.parent_id = parent_id
        page.updated_by = current_user.id
        page.updated_at = datetime.utcnow()
        
        # Update slug if title changed
        new_slug = slugify(title)
        if new_slug != page.slug:
            # Check for duplicate slug
            existing = WikiPage.query.filter(
                WikiPage.project_id == project_id,
                WikiPage.slug == new_slug,
                WikiPage.is_active == True,
                WikiPage.id != page.id
            ).first()
            
            if existing:
                counter = 1
                test_slug = f"{new_slug}-{counter}"
                while WikiPage.query.filter(
                    WikiPage.project_id == project_id,
                    WikiPage.slug == test_slug,
                    WikiPage.is_active == True,
                    WikiPage.id != page.id
                ).first():
                    counter += 1
                    test_slug = f"{new_slug}-{counter}"
                page.slug = test_slug
            else:
                page.slug = new_slug
        
        db.session.commit()
        
        flash(f'Wiki page "{title}" updated successfully!', 'success')
        return redirect(url_for('wiki.view', project_id=project_id, page_id=page.id))
    
    # GET request - show form
    # Get all pages except this one and its descendants for parent selection
    descendants = page.get_all_descendants()
    descendant_ids = [d.id for d in descendants] + [page.id]
    
    all_pages = WikiPage.query.filter(
        WikiPage.project_id == project_id,
        WikiPage.is_active == True,
        ~WikiPage.id.in_(descendant_ids)
    ).order_by(WikiPage.title).all()
    
    return render_template('wiki/edit.html',
                         project=project,
                         page=page,
                         all_pages=all_pages)


@wiki_bp.route('/projects/<int:project_id>/wiki/<int:page_id>/delete', methods=['POST'])
@login_required
def delete(project_id, page_id):
    """Delete a wiki page (soft delete)."""
    project = Project.query.get_or_404(project_id)
    page = WikiPage.query.filter_by(id=page_id, project_id=project_id).first_or_404()
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    # Soft delete
    page.is_active = False
    page.updated_by = current_user.id
    page.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Wiki page "{page.title}" deleted successfully!', 'success')
    return redirect(url_for('wiki.index', project_id=project_id))


@wiki_bp.route('/projects/<int:project_id>/wiki/search')
@login_required
def search(project_id):
    """Search wiki pages."""
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access to project
    if current_user not in project.members and current_user.role.value != 'admin':
        abort(403)
    
    query = request.args.get('q', '').strip()
    
    if not query:
        flash('Please enter a search term.', 'info')
        return redirect(url_for('wiki.index', project_id=project_id))
    
    # Search in title and content
    search_pattern = f'%{query}%'
    pages = WikiPage.query.filter(
        WikiPage.project_id == project_id,
        WikiPage.is_active == True,
        or_(
            WikiPage.title.ilike(search_pattern),
            WikiPage.content.ilike(search_pattern)
        )
    ).order_by(WikiPage.title).all()
    
    return render_template('wiki/search.html',
                         project=project,
                         pages=pages,
                         query=query)
