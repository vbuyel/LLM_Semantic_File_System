import { state } from '../state.js';

export const Sidebar = {
    render() {
        const activeSource = state.get('storageSource');
        
        return `
            <aside class="sidebar">
                <div class="sidebar__header">
                    <div class="logo-wrapper">
                        <i data-lucide="layers" class="text-accent"></i>
                    </div>
                    <span class="logo-text">Semantic FS</span>
                </div>
                
                <nav class="sidebar__nav">
                    <div class="sidebar__section-title">Storage</div>
                    
                    <div class="sidebar__item ${activeSource === 'local' ? 'sidebar__item--active' : ''}" data-source="local">
                        <i data-lucide="hard-drive"></i>
                        <span>Local Files</span>
                    </div>
                    
                    <div class="sidebar__item ${activeSource === 'drive' ? 'sidebar__item--active' : ''}" data-source="drive">
                        <i data-lucide="cloud"></i>
                        <span>Google Drive</span>
                        <div class="status-dot status-dot--online"></div>
                    </div>
                    
                    <div class="sidebar__item ${activeSource === 'gcs' ? 'sidebar__item--active' : ''}" data-source="gcs">
                        <i data-lucide="database"></i>
                        <span>Cloud Storage</span>
                        <div class="status-dot status-dot--online"></div>
                    </div>

                    <div class="sidebar__section-title">Views</div>
                    <div class="sidebar__item">
                        <i data-lucide="star"></i>
                        <span>Favorites</span>
                    </div>
                    <div class="sidebar__item">
                        <i data-lucide="clock"></i>
                        <span>Recent</span>
                    </div>
                </nav>
                
                <div class="sidebar__footer">
                    <div class="sidebar__item" id="logout-btn">
                        <i data-lucide="log-out"></i>
                        <span>Logout</span>
                    </div>
                </div>
            </aside>
        `;
    },

    attachEvents() {
        const items = document.querySelectorAll('.sidebar__item[data-source]');
        items.forEach(item => {
            item.onclick = async () => {
                const source = item.dataset.source;
                state.set('storageSource', source);
                
                // Reset path when switching source
                state.set('currentPath', '/');
                state.set('breadcrumbs', [{ name: 'Root', path: '/' }]);
                
                // Trigger reload
                window.app.loadInitialData();
            };
        });
    }
};
