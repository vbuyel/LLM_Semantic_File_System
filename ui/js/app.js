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
        // Subscribe to state changes
        state.subscribe(() => this.render());

        // Check for existing session
        const user = api.auth.getUser();
        if (user) {
            state.set('user', user);
            this.loadInitialData();
        } else {
            this.render();
        }
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
