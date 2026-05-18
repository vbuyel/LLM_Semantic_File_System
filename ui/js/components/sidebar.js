import { state } from '../state.js';

export const Sidebar = {
    toggle(isOpen) {
        const sidebar = document.getElementById('app-sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (sidebar) {
            if (isOpen) {
                sidebar.classList.add('sidebar--open');
            } else {
                sidebar.classList.remove('sidebar--open');
            }
        }
        if (backdrop) {
            if (isOpen) {
                backdrop.classList.add('active');
            } else {
                backdrop.classList.remove('active');
            }
        }
    },

    render() {
        const activeSource = state.get('storageSource');
        const user = state.get('user');
        const statusClass = (user && user.isGuest) ? 'status-dot--guest' : 'status-dot--online';

        return `
            <aside class="sidebar" id="app-sidebar">
                <div class="sidebar__mobile-close">
                    <button id="sidebar-close-btn" class="sidebar__close-btn" aria-label="Close sidebar">
                        <i data-lucide="x"></i>
                    </button>
                </div>
                <div class="sidebar__header">
                    <div class="logo-wrapper">
                        <i data-lucide="layers" class="text-accent"></i>
                    </div>
                    <span class="logo-text">Semantic FS</span>
                </div>

                <nav class="sidebar__nav">
                    <div class="sidebar__section-title">Storage</div>

                    <div class="sidebar__item ${activeSource === 'drive' ? 'sidebar__item--active' : ''}" data-source="drive">
                        <i data-lucide="cloud"></i>
                        <span>Google Drive</span>
                        <div class="status-dot ${statusClass}"></div>
                    </div>

                    <div class="sidebar__item ${activeSource === 'gcs' ? 'sidebar__item--active' : ''}" data-source="gcs">
                        <i data-lucide="database"></i>
                        <span>Cloud Storage</span>
                        <div class="status-dot status-dot--online"></div>
                    </div>

                </nav>

                <div class="sidebar__footer">
                    ${this.renderFooter()}
                </div>
            </aside>
            <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
        `;
    },

    renderFooter() {
        const user = state.get('user');
        
        if (user && user.isGuest) {
            return `
                <div class="sidebar__guest-warning">
                    <i data-lucide="alert-triangle"></i>
                    <span>You have to sign in to see your Google Drive files</span>
                </div>
                <div class="sidebar__item" id="sign-in-google-guest">
                    <i data-lucide="log-in"></i>
                    <span>Sign in with Google</span>
                </div>
                <div class="sidebar__item" id="logout-btn">
                    <i data-lucide="log-out"></i>
                    <span>Logout</span>
                </div>
            `;
        }
        
        if (user && user.picture) {
            return `
                <div class="sidebar__item" id="logout-btn">
                    <img src="${user.picture}" alt="${user.name}" class="avatar-avatar" style="width: 28px; height: 28px; border-radius: 50%;" />
                    <span>Logout</span>
                    <i data-lucide="log-out"></i>
                </div>
            `;
        }
        
        return `
            <div class="sidebar__item" id="logout-btn">
                <i data-lucide="log-out"></i>
                <span>Logout</span>
            </div>
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
                
                // Close sidebar on mobile when switching
                this.toggle(false);

                // Trigger reload
                window.app.loadInitialData();
            };
        });

        const signInGoogleGuest = document.getElementById('sign-in-google-guest');
        if (signInGoogleGuest) {
            signInGoogleGuest.onclick = async () => {
                window.location.href = 'http://localhost:8000/auth/google/url';
            };
        }

        const closeBtn = document.getElementById('sidebar-close-btn');
        if (closeBtn) {
            closeBtn.onclick = () => {
                this.toggle(false);
            };
        }

        const backdrop = document.getElementById('sidebar-backdrop');
        if (backdrop) {
            backdrop.onclick = () => {
                this.toggle(false);
            };
        }
    }
};
