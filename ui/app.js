const API_BASE = 'http://localhost:8000';

class FileSystemApp {
    constructor() {
        this.currentPath = '/';
        this.files = [];
        this.selectedItems = [];
        this.isGridView = false;
        this.history = [];
        this.historyIndex = -1;
        this.uploadQueue = [];

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDirectory('/');
    }

    bindEvents() {
        document.querySelectorAll('.nav-item[data-path]').forEach(item => {
            item.addEventListener('click', () => this.navigateTo(item.dataset.path));
        });

        document.getElementById('btn-back').addEventListener('click', () => this.goBack());
        document.getElementById('btn-forward').addEventListener('click', () => this.goForward());
        document.getElementById('btn-up').addEventListener('click', () => this.goUp());
        document.getElementById('btn-view').addEventListener('click', () => this.toggleView());
        document.getElementById('btn-search').addEventListener('click', () => this.semanticSearch());
        document.getElementById('semantic-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.semanticSearch();
        });

        document.getElementById('file-list').addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showContextMenu(e.clientX, e.clientY);
        });

        document.getElementById('file-list').addEventListener('click', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                this.handleFileClick(fileItem);
            }
        });

        document.addEventListener('click', () => this.hideContextMenu());

        document.querySelectorAll('.context-menu-item').forEach(item => {
            item.addEventListener('click', () => this.handleContextAction(item.dataset.action));
        });

        document.getElementById('modal-close').addEventListener('click', () => this.closeUploadModal());
        document.getElementById('upload-modal').addEventListener('click', (e) => {
            if (e.target.id === 'upload-modal') this.closeUploadModal();
        });

        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        document.getElementById('btn-browse').addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete' && this.selectedItems.length > 0) {
                this.deleteSelected();
            }
            if (e.key === 'Enter' && this.selectedItems.length === 1) {
                this.openItem(this.selectedItems[0]);
            }
        });
    }

    async loadDirectory(path) {
        try {
            const response = await fetch(`${API_BASE}/files?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error('Failed to load directory');
            this.files = await response.json();
            this.renderFiles();
            this.updateBreadcrumb(path);
            this.currentPath = path;
            this.addToHistory(path);
            this.updateNavigationButtons();
        } catch (error) {
            this.showToast('Failed to load directory: ' + error.message, 'error');
        }
    }

    renderFiles() {
        const container = document.getElementById('file-list');
        container.innerHTML = '';

        if (this.files.length === 0) {
            container.innerHTML = '<div class="empty-state">No files found</div>';
            return;
        }

        this.files.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = `file-item ${file.isDirectory ? 'folder-item' : ''}`;
            item.dataset.index = index;
            item.dataset.name = file.name;

            item.innerHTML = `
                <div class="col-name">
                    <span class="file-icon">${this.getFileIcon(file)}</span>
                    <span class="file-name">${file.name}</span>
                </div>
                <span class="file-type col-type">${file.isDirectory ? 'Folder' : file.type}</span>
                <span class="file-size col-size">${file.isDirectory ? '--' : this.formatSize(file.size)}</span>
                <span class="file-modified col-modified">${file.modified || 'Unknown'}</span>
            `;

            item.addEventListener('dblclick', () => this.openItem(file));

            container.appendChild(item);
        });

        this.updateStatusBar();
    }

    getFileIcon(file) {
        if (file.isDirectory) return '📁';
        
        const ext = file.name.split('.').pop()?.toLowerCase();
        const icons = {
            'pdf': '📕', 'doc': '📄', 'docx': '📄', 'txt': '📝',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'mp4': '🎬', 'avi': '🎬', 'mkv': '🎬',
            'zip': '🗜️', 'rar': '🗜️', '7z': '🗜️',
            'js': '📜', 'ts': '📜', 'py': '🐍', 'java': '☕',
            'html': '🌐', 'css': '🎨', 'json': '📋'
        };
        return icons[ext] || '📄';
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    handleFileClick(item) {
        const index = parseInt(item.dataset.index);
        const file = this.files[index];

        if (!item.ctrlKey && !item.metaKey) {
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('selected'));
        }

        item.classList.toggle('selected');
        
        this.selectedItems = Array.from(document.querySelectorAll('.file-item.selected'))
            .map(el => this.files[parseInt(el.dataset.index)]);
    }

    openItem(file) {
        if (file.isDirectory) {
            this.loadDirectory(file.path || this.currentPath + '/' + file.name);
        } else {
            this.showToast(`Opening ${file.name}...`, 'success');
        }
    }

    navigateTo(path) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        document.querySelector(`[data-path="${path}"]`)?.classList.add('active');
        this.loadDirectory(path);
    }

    goBack() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.loadDirectory(this.history[this.historyIndex]);
        }
    }

    goForward() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.loadDirectory(this.history[this.historyIndex]);
        }
    }

    goUp() {
        const parts = this.currentPath.split('/').filter(Boolean);
        if (parts.length > 0) {
            parts.pop();
            const newPath = '/' + parts.join('/');
            this.loadDirectory(newPath || '/');
        }
    }

    addToHistory(path) {
        if (this.history[this.historyIndex] !== path) {
            this.history = this.history.slice(0, this.historyIndex + 1);
            this.history.push(path);
            this.historyIndex = this.history.length - 1;
        }
    }

    updateNavigationButtons() {
        document.getElementById('btn-back').disabled = this.historyIndex <= 0;
        document.getElementById('btn-forward').disabled = this.historyIndex >= this.history.length - 1;
        document.getElementById('btn-up').disabled = this.currentPath === '/';
    }

    updateBreadcrumb(path) {
        const parts = path.split('/').filter(Boolean);
        const breadcrumb = document.querySelector('.breadcrumb');
        
        let html = '<span class="breadcrumb-item" data-path="/">This PC</span>';
        
        parts.forEach((part, index) => {
            const currentPath = '/' + parts.slice(0, index + 1).join('/');
            html += `<span class="breadcrumb-separator">/</span>`;
            html += `<span class="breadcrumb-item ${index === parts.length - 1 ? 'current' : ''}" data-path="${currentPath}">${part}</span>`;
        });

        breadcrumb.innerHTML = html;

        breadcrumb.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => this.loadDirectory(item.dataset.path));
        });
    }

    toggleView() {
        this.isGridView = !this.isGridView;
        const fileList = document.getElementById('file-list');
        fileList.classList.toggle('grid-view', this.isGridView);
        document.getElementById('view-icon').textContent = this.isGridView ? '▤' : '▦';
    }

    async semanticSearch() {
        const query = document.getElementById('semantic-search').value.trim();
        if (!query) return;

        try {
            const response = await fetch(`${API_BASE}/ai_agent?text=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search failed');
            
            const result = await response.json();
            this.files = result.files || [];
            this.renderFiles();
            this.showToast(`Found ${this.files.length} results`, 'success');
        } catch (error) {
            this.showToast('Search failed: ' + error.message, 'error');
        }
    }

    showContextMenu(x, y) {
        const menu = document.getElementById('context-menu');
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.classList.add('active');
    }

    hideContextMenu() {
        document.getElementById('context-menu').classList.remove('active');
    }

    handleContextAction(action) {
        this.hideContextMenu();

        switch (action) {
            case 'open':
                if (this.selectedItems.length === 1) {
                    this.openItem(this.selectedItems[0]);
                }
                break;
            case 'download':
                this.downloadSelected();
                break;
            case 'rename':
                this.renameSelected();
                break;
            case 'move':
                this.moveSelected();
                break;
            case 'delete':
                this.deleteSelected();
                break;
        }
    }

    async deleteSelected() {
        if (this.selectedItems.length === 0) return;

        const confirmed = confirm(`Delete ${this.selectedItems.length} item(s)?`);
        if (!confirmed) return;

        try {
            for (const item of this.selectedItems) {
                await fetch(`${API_BASE}/files/delete`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: item.path || this.currentPath + '/' + item.name })
                });
            }
            this.showToast('Files deleted successfully', 'success');
            this.loadDirectory(this.currentPath);
        } catch (error) {
            this.showToast('Delete failed: ' + error.message, 'error');
        }
    }

    async downloadSelected() {
        if (this.selectedItems.length === 0) return;
        
        for (const item of this.selectedItems) {
            const link = document.createElement('a');
            link.href = `${API_BASE}/files/download?path=${encodeURIComponent(item.path || this.currentPath + '/' + item.name)}`;
            link.download = item.name;
            link.click();
        }
    }

    renameSelected() {
        if (this.selectedItems.length !== 1) return;
        
        const newName = prompt('Enter new name:', this.selectedItems[0].name);
        if (!newName || newName === this.selectedItems[0].name) return;

        this.renameFile(this.selectedItems[0], newName);
    }

    async renameFile(file, newName) {
        try {
            await fetch(`${API_BASE}/files/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: file.path || this.currentPath + '/' + file.name,
                    newName
                })
            });
            this.showToast('File renamed successfully', 'success');
            this.loadDirectory(this.currentPath);
        } catch (error) {
            this.showToast('Rename failed: ' + error.message, 'error');
        }
    }

    moveSelected() {
        if (this.selectedItems.length === 0) return;
        
        const targetPath = prompt('Enter target path:');
        if (!targetPath) return;

        this.moveFiles(this.selectedItems, targetPath);
    }

    async moveFiles(files, targetPath) {
        try {
            for (const file of files) {
                await fetch(`${API_BASE}/files/move`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sourcePath: file.path || this.currentPath + '/' + file.name,
                        targetPath: targetPath + '/' + file.name
                    })
                });
            }
            this.showToast('Files moved successfully', 'success');
            this.loadDirectory(this.currentPath);
        } catch (error) {
            this.showToast('Move failed: ' + error.message, 'error');
        }
    }

    handleFiles(fileList) {
        Array.from(fileList).forEach(file => {
            this.uploadQueue.push(file);
        });
        this.renderUploadQueue();
    }

    renderUploadQueue() {
        const uploadZone = document.getElementById('upload-zone');
        const fileListHtml = this.uploadQueue.map((file, index) => `
            <div class="upload-file-item">
                <span class="file-icon">${this.getFileIcon({ name: file.name })}</span>
                <div class="upload-file-info">
                    <div class="upload-file-name">${file.name}</div>
                    <div class="upload-file-size">${this.formatSize(file.size)}</div>
                </div>
                <button class="btn-remove" data-index="${index}">✕</button>
            </div>
        `).join('');

        uploadZone.innerHTML = `
            <div class="upload-file-list">${fileListHtml}</div>
            <button class="btn-upload" id="btn-start-upload">Upload ${this.uploadQueue.length} file(s)</button>
        `;

        document.getElementById('btn-start-upload').addEventListener('click', () => this.startUpload());
    }

    async startUpload() {
        if (this.uploadQueue.length === 0) return;

        const btn = document.getElementById('btn-start-upload');
        btn.disabled = true;
        btn.textContent = 'Uploading...';

        for (const file of this.uploadQueue) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', this.currentPath);

            try {
                await fetch(`${API_BASE}/files/upload`, {
                    method: 'POST',
                    body: formData
                });
            } catch (error) {
                this.showToast(`Failed to upload ${file.name}`, 'error');
            }
        }

        this.uploadQueue = [];
        this.closeUploadModal();
        this.loadDirectory(this.currentPath);
        this.showToast('Files uploaded successfully', 'success');
    }

    openUploadModal() {
        document.getElementById('upload-modal').classList.add('active');
        document.getElementById('upload-zone').innerHTML = `
            <div class="upload-icon">📤</div>
            <p>Drag and drop files here</p>
            <p>or</p>
            <button class="btn-browse" id="btn-browse">Browse Files</button>
            <input type="file" id="file-input" multiple hidden>
        `;
        document.getElementById('btn-browse').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });
        document.getElementById('file-input').addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }

    closeUploadModal() {
        document.getElementById('upload-modal').classList.remove('active');
        this.uploadQueue = [];
    }

    updateStatusBar() {
        document.getElementById('status-text').textContent = `${this.files.length} items`;
        const selection = document.querySelectorAll('.file-item.selected').length;
        document.getElementById('selection-info').textContent = selection > 0 ? `${selection} selected` : '';
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="toast-message">${message}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new FileSystemApp();
});
