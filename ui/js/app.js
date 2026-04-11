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
        const files = await api.files.getFiles();
        state.set('files', files);
    }

    render() {
        const user = state.get('user');

        if (!user) {
            Auth.render();
            return;
        }

        const files = state.get('files');
        
        this.appElement.innerHTML = `
            <div class="layout-dashboard">
                ${Sidebar.render()}
                <main class="main-content">
                    ${AIInterface.render()}
                    ${Explorer.render(files)}
                </main>
            </div>
        `;

        // Re-initialize icons
        lucide.createIcons();

        // Attach events
        this.attachEvents();
    }

    attachEvents() {
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.onclick = async () => {
                await api.auth.logout();
                state.set('user', null);
                state.set('files', []);
            };
        }
    }
}

// Start application
new App();
