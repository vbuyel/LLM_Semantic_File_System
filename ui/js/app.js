import { api } from './api.js';
import { state } from './state.js';
import { Auth } from './components/auth.js';
import { Sidebar } from './components/sidebar.js';
import { Explorer } from './components/explorer.js';
import { AIInterface } from './components/ai-interface.js';

class App {
    constructor() {
        this.appElement = document.getElementById('app');
        this.init();
    }

    async init() {
        // Load user from localStorage on startup
        const savedUser = api.auth.getUser();
        if (savedUser) {
            state.set('user', savedUser);
            AIInterface.init(savedUser.email);
        }

        const queryParams = new URLSearchParams(window.location.search);
        const code = queryParams.get('code');
        const oauthState = queryParams.get('state');

        if (code && oauthState) {
            try {
                const user = await api.auth.loginWithGoogle(code, oauthState);
                state.set('user', user);
                AIInterface.init(user.email);
            } catch (err) {
                console.error('[App] OAuth callback error:', err);
            }
            window.history.replaceState({}, '', '/');
        } else if (window.location.pathname === '/auth/google') {
            this.appElement.innerHTML = `
                <div class="auth fade-in">
                    <div class="auth__container" style="justify-content: center; text-align: center;">
                        <h2>Processing authorization...</h2>
                    </div>
                </div>
            `;
        }

        state.subscribe(() => this.render());
        this.render();
    }

    async loadInitialData() {
        state.set('isLoading', true);
        try {
            const path = state.get('currentPath');
            const files = await api.files.getFiles(path);
            state.set('files', files);
        } catch (error) {
            console.error('Failed to load files:', error);
            // In a real app, show a toast here
        } finally {
            state.set('isLoading', false);
        }
    }

    render() {
        const user = state.get('user');

        if (!user) {
            Auth.render();
            return;
        }

        const files = state.get('files');
        const isLoading = state.get('isLoading');
        
        this.appElement.innerHTML = `
            <div class="layout-dashboard">
                ${Sidebar.render()}
                <main class="main-content">
                    ${AIInterface.render()}
                    <div class="content-body">
                        ${Explorer.render(files, isLoading)}
                    </div>
                </main>
            </div>
        `;

        // Re-initialize icons
        lucide.createIcons();

        // Attach events
        this.attachEvents();
    }

    attachEvents() {
        // Global escape to clear search
        document.onkeydown = (e) => {
            if (e.key === 'Escape' && state.get('isSearching')) {
                state.set('isSearching', false);
                state.set('searchResult', null);
            }
        };

        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.onclick = async () => {
                await api.auth.logout();
                state.set('user', null);
                state.set('files', []);
            };
        }

        // Component specific events
        Sidebar.attachEvents();
        Explorer.attachEvents();
        AIInterface.attachEvents();
    }
}

// Start application
window.app = new App();
