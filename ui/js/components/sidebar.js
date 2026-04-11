import { state } from '../state.js';

export const Sidebar = {
    render() {
        return `
            <aside class="sidebar">
                <div class="sidebar__header">
                    <i data-lucide="layers" class="text-accent"></i>
                    <span style="font-weight: 600; font-size: 1.1rem">Semantic</span>
                </div>
                
                <nav class="sidebar__nav">
                    <div class="sidebar__item sidebar__item--active">
                        <i data-lucide="folder"></i>
                        <span>All Files</span>
                    </div>
                    <div class="sidebar__item">
                        <i data-lucide="star"></i>
                        <span>Favorites</span>
                    </div>
                    <div class="sidebar__item">
                        <i data-lucide="clock"></i>
                        <span>Recent</span>
                    </div>
                    
                    <div class="sidebar__section-title">Integrations</div>
                    <div class="integration">
                        <div class="sidebar__item" style="padding: 0; background: none">
                            <i data-lucide="cloud"></i>
                            <span>Google Drive</span>
                        </div>
                        <div class="status-dot"></div>
                    </div>
                    <div class="integration">
                        <div class="sidebar__item" style="padding: 0; background: none">
                            <i data-lucide="database"></i>
                            <span>GCS</span>
                        </div>
                        <div class="status-dot"></div>
                    </div>
                </nav>
                
                <div class="sidebar__footer" style="padding: 0 var(--space-lg)">
                    <div class="sidebar__item" id="logout-btn">
                        <i data-lucide="log-out"></i>
                        <span>Logout</span>
                    </div>
                </div>
            </aside>
        `;
    }
};
