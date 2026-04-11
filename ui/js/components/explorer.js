import { state } from '../state.js';
import { api } from '../api.js';

const escapeHtml = (str) => {
    if (typeof str !== 'string') return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
};

export const Explorer = {
    render(files, isLoading) {
        const breadcrumbs = state.get('breadcrumbs');
        const viewMode = state.get('activeView');

        const breadcrumbHtml = breadcrumbs.map((b, i) => `
            <span class="breadcrumb-item" data-path="${escapeHtml(b.path)}">${escapeHtml(b.name)}</span>
            ${i < breadcrumbs.length - 1 ? '<i data-lucide="chevron-right" size="14"></i>' : ''}
        `).join('');

        if (isLoading) {
            return `
                <div class="explorer">
                    <div class="explorer__toolbar">
                        <div class="breadcrumbs">${breadcrumbHtml}</div>
                    </div>
                    <div class="explorer__loading">
                        <div class="spinner"></div>
                        <p>Accessing storage...</p>
                    </div>
                </div>
            `;
        }

        const itemsHtml = files.map(file => `
            <div class="explorer__item fade-in" data-path="${escapeHtml(file.path)}" data-type="${file.isDirectory ? 'folder' : 'file'}" data-name="${escapeHtml(file.name)}">
                <div class="explorer__item-content">
                    <div class="explorer__icon">
                        <i data-lucide="${file.isDirectory ? 'folder' : 'file-text'}" size="28"></i>
                    </div>
                    <div class="explorer__details">
                        <div class="explorer__name">${escapeHtml(file.name)}</div>
                        <div class="explorer__meta">${escapeHtml(file.modified || '')} • ${file.size ? this.formatSize(file.size) : '--'}</div>
                    </div>
                </div>
                <div class="explorer__actions">
                    <button class="action-btn delete-btn" title="Delete">
                        <i data-lucide="trash-2" size="16"></i>
                    </button>
                    <button class="action-btn rename-btn" title="Rename">
                        <i data-lucide="edit-3" size="16"></i>
                    </button>
                </div>
            </div>
        `).join('');

        return `
            <div class="explorer explorer--${viewMode}">
                <div class="explorer__toolbar">
                    <div class="breadcrumbs">${breadcrumbHtml}</div>
                    <div class="explorer__controls">
                        <button id="upload-btn" class="btn btn--primary">
                            <i data-lucide="upload"></i>
                            <span>Upload</span>
                        </button>
                    </div>
                </div>
                <div class="explorer__grid">
                    ${files.length > 0 ? itemsHtml : '<div class="explorer__empty">No files found in this directory</div>'}
                </div>
            </div>
        `;
    },

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },

    attachEvents() {
        // Navigation (Double click)
        const items = document.querySelectorAll('.explorer__item');
        items.forEach(item => {
            item.ondblclick = () => {
                if (item.dataset.type === 'folder') {
                    const path = item.dataset.path;
                    const name = item.dataset.name;
                    
                    const breadcrumbs = state.get('breadcrumbs');
                    state.set('breadcrumbs', [...breadcrumbs, { name, path }]);
                    state.set('currentPath', path);
                    
                    window.app.loadInitialData();
                }
            };

            // Actions
            const deleteBtn = item.querySelector('.delete-btn');
            if (deleteBtn) {
                deleteBtn.onclick = async (e) => {
                    e.stopPropagation();
                    if (confirm(`Delete ${item.dataset.name}?`)) {
                        await api.files.deleteFile(item.dataset.path);
                        window.app.loadInitialData();
                    }
                };
            }
        });

        // Breadcrumb clicks
        const bItems = document.querySelectorAll('.breadcrumb-item');
        bItems.forEach((item, index) => {
            item.onclick = () => {
                const breadcrumbs = state.get('breadcrumbs');
                const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
                state.set('breadcrumbs', newBreadcrumbs);
                state.set('currentPath', item.dataset.path);
                window.app.loadInitialData();
            };
        });

        // Upload
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.onclick = () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.onchange = async () => {
                    if (input.files.length > 0) {
                        state.set('isLoading', true);
                        try {
                            await api.files.uploadFile(input.files[0], state.get('currentPath'));
                            window.app.loadInitialData();
                        } catch (e) {
                            alert('Upload failed');
                            state.set('isLoading', false);
                        }
                    }
                };
                input.click();
            };
        }
    }
};
