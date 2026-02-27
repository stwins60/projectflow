/**
 * Project Manager - Main JavaScript
 */

(function() {
    'use strict';

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initThemeToggle();
        initSidebar();
        initTooltips();
        initFormValidation();
        initAlertDismiss();
        initConfirmDialogs();
        initSearchShortcut();
    });

    /**
     * Theme Toggle (Dark/Light Mode)
     */
    function initThemeToggle() {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;

        // Load saved theme or use system preference
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        
        document.documentElement.setAttribute('data-theme', theme);
        updateThemeIcon(theme);

        toggle.addEventListener('click', function() {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        const icon = document.querySelector('#themeToggle i');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
        }
    }

    /**
     * Sidebar Toggle (Mobile)
     */
    function initSidebar() {
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        if (!sidebarToggle || !sidebar) return;

        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            if (overlay) overlay.classList.toggle('show');
        });

        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('show');
                overlay.classList.remove('show');
            });
        }

        // Close sidebar on window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 992) {
                sidebar.classList.remove('show');
                if (overlay) overlay.classList.remove('show');
            }
        });
    }

    /**
     * Bootstrap Tooltips
     */
    function initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(function(tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Form Validation
     */
    function initFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        
        forms.forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    }

    /**
     * Alert Auto-dismiss
     */
    function initAlertDismiss() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        
        alerts.forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, 5000);
        });
    }

    /**
     * Confirm Dialogs
     */
    function initConfirmDialogs() {
        document.querySelectorAll('[data-confirm]').forEach(function(el) {
            el.addEventListener('click', function(e) {
                const message = this.dataset.confirm || 'Are you sure?';
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    /**
     * Search Shortcut (Ctrl/Cmd + K) and functionality
     */
    function initSearchShortcut() {
        const searchInput = document.getElementById('globalSearch');
        if (!searchInput) return;

        // Focus on Ctrl/Cmd + K
        document.addEventListener('keydown', function(e) {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
            // Close on Escape
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.blur();
            }
        });

        // Search on Enter
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && this.value.trim()) {
                e.preventDefault();
                window.location.href = '/issues?search=' + encodeURIComponent(this.value.trim());
            }
        });
    }

    /**
     * Kanban Drag and Drop
     */
    window.initKanban = function() {
        const cards = document.querySelectorAll('.kanban-card');
        const columns = document.querySelectorAll('.kanban-column-body');

        cards.forEach(function(card) {
            card.addEventListener('dragstart', handleDragStart);
            card.addEventListener('dragend', handleDragEnd);
        });

        columns.forEach(function(column) {
            column.addEventListener('dragover', handleDragOver);
            column.addEventListener('drop', handleDrop);
            column.addEventListener('dragenter', handleDragEnter);
            column.addEventListener('dragleave', handleDragLeave);
        });
    };

    let draggedCard = null;

    function handleDragStart(e) {
        draggedCard = this;
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.dataset.issueId);
    }

    function handleDragEnd() {
        this.classList.remove('dragging');
        document.querySelectorAll('.kanban-column-body').forEach(function(col) {
            col.classList.remove('drag-over');
        });
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDragEnter(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    }

    function handleDragLeave() {
        this.classList.remove('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        this.classList.remove('drag-over');

        if (!draggedCard) return;

        const newStatus = this.parentElement.dataset.status;
        const issueId = draggedCard.dataset.issueId;

        // Move card visually
        this.appendChild(draggedCard);

        // Update issue status via API
        updateIssueStatus(issueId, newStatus);

        // Update count badges
        updateColumnCounts();
    }

    function updateIssueStatus(issueId, status) {
        fetch(`/issues/${issueId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ status: status })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Issue status updated', 'success');
            } else {
                showToast('Failed to update status', 'danger');
            }
        })
        .catch(() => {
            showToast('Failed to update status', 'danger');
        });
    }

    function updateColumnCounts() {
        document.querySelectorAll('.kanban-column').forEach(function(col) {
            const count = col.querySelectorAll('.kanban-card').length;
            const badge = col.querySelector('.kanban-count');
            if (badge) badge.textContent = count;
        });
    }

    /**
     * Get CSRF Token
     */
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    /**
     * Toast Notifications
     */
    window.showToast = function(message, type = 'info') {
        const container = document.getElementById('toastContainer') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    };

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
        return container;
    }

    /**
     * Format Date Relative
     */
    window.formatRelativeDate = function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (seconds < 60) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        
        return date.toLocaleDateString();
    };

    /**
     * Copy to Clipboard
     */
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard', 'success');
        }).catch(function() {
            showToast('Failed to copy', 'danger');
        });
    };

    /**
     * Debounce Function
     */
    window.debounce = function(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    /**
     * Live Search
     */
    window.initLiveSearch = function(inputSelector, listSelector, itemSelector) {
        const input = document.querySelector(inputSelector);
        const list = document.querySelector(listSelector);
        
        if (!input || !list) return;

        input.addEventListener('input', debounce(function() {
            const query = this.value.toLowerCase();
            const items = list.querySelectorAll(itemSelector);
            
            items.forEach(function(item) {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? '' : 'none';
            });
        }, 200));
    };

    /**
     * File Upload Preview
     */
    window.initFileUpload = function(inputId, previewId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        
        if (!input || !preview) return;

        input.addEventListener('change', function() {
            preview.innerHTML = '';
            
            Array.from(this.files).forEach(function(file) {
                const item = document.createElement('div');
                item.className = 'd-flex align-items-center gap-2 mb-2';
                
                const icon = document.createElement('i');
                icon.className = getFileIcon(file.type);
                
                const name = document.createElement('span');
                name.textContent = file.name;
                
                const size = document.createElement('small');
                size.className = 'text-muted';
                size.textContent = formatFileSize(file.size);
                
                item.appendChild(icon);
                item.appendChild(name);
                item.appendChild(size);
                preview.appendChild(item);
            });
        });
    };

    function getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) return 'bi bi-file-image text-success';
        if (mimeType.startsWith('video/')) return 'bi bi-file-play text-info';
        if (mimeType.includes('pdf')) return 'bi bi-file-pdf text-danger';
        if (mimeType.includes('word')) return 'bi bi-file-word text-primary';
        if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'bi bi-file-excel text-success';
        return 'bi bi-file-earmark text-secondary';
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Mark Notifications as Read
     */
    window.markNotificationRead = function(notificationId) {
        fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        }).then(response => {
            if (response.ok) {
                const badge = document.querySelector('.notification-badge');
                if (badge) {
                    const count = parseInt(badge.textContent) - 1;
                    if (count <= 0) {
                        badge.remove();
                    } else {
                        badge.textContent = count;
                    }
                }
            }
        });
    };

    /**
     * Auto-resize Textarea
     */
    window.autoResize = function(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    };

    // Auto-resize all textareas with data-autoresize
    document.querySelectorAll('textarea[data-autoresize]').forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            autoResize(this);
        });
        autoResize(textarea);
    });

})();
