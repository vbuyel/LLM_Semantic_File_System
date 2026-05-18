import { api } from './api.js';
import { state } from './state.js';
import { Auth } from './components/auth.js';
import { Sidebar } from './components/sidebar.js';
import { Explorer } from './components/explorer.js';
import { AIInterface } from './components/ai-interface.js';
import { StatusBar } from './components/status-bar.js';
import { AIThinking } from './components/events/ai-thinking.js';
import { Events } from './components/events/base.js';
import { FileOps } from './components/events/files-ops.js';

class App {
    constructor() {
        this.appElement = document.getElementById('app');
        this.init();
    }

    async init() {
        const savedUser = api.auth.getUser();
        if (savedUser) {
            state.set('user', savedUser);
            this._startServices(savedUser.email || savedUser.id);
        }

        const queryParams = new URLSearchParams(window.location.search);
        const code = queryParams.get('code');
        const oauthState = queryParams.get('state');

        if (code && oauthState) {
            try {
                const user = await api.auth.loginWithGoogle(code, oauthState);
                state.set('user', user);
                this._startServices(user.email || user.id);
            } catch (err) {
                console.error('[App] OAuth callback error:', err);
            }
            window.history.replaceState({}, '', window.location.pathname);
        } else if (window.location.pathname.endsWith('/auth/google')) {
            this.appElement.innerHTML = `
                <div class="auth fade-in">
                    <div class="auth__container" style="justify-content: center; text-align: center;">
                        <h2>Processing authorization...</h2>
                    </div>
                </div>
            `;
        }

        state.subscribe((data) => {
            if (data.user) {
                this._startServices(data.user.email || data.user.id);
            }
        });

        Events.subscribe((eventData) => {
            const span = document.querySelector('.ai-thinking > span');
            if (span) span.textContent = AIThinking.getLastEventText();
            StatusBar.showEvent(eventData);
        });

        state.subscribe(() => this.render());
        this.render();
    }

    _startServices(email) {
        Events.reconnect(email);
        AIThinking.init(email);
        FileOps.init(email);
    }

    async loadInitialData() {
        state.set('isLoading', true);
        try {
            const path = state.get('currentPath');
            const files = await api.files.getFiles(path);
            state.set('files', files);
        } catch (error) {
            console.error('Failed to load files:', error);
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
                    <header class="mobile-header">
                        <button id="mobile-menu-toggle" class="mobile-header__toggle" aria-label="Open menu">
                            <i data-lucide="menu"></i>
                        </button>
                        <div class="mobile-header__logo">
                            <i data-lucide="layers" class="text-accent"></i>
                            <span class="logo-text">Semantic FS</span>
                        </div>
                        <div style="width: 32px;"></div> <!-- visual spacer to balance the flex layout -->
                    </header>
                    ${StatusBar.render()}
                    ${AIInterface.render()}
                    <div class="content-body">
                        ${Explorer.render(files, isLoading)}
                    </div>
                </main>
            </div>
        `;

        lucide.createIcons();
        this.attachEvents();
    }

    attachEvents() {
        document.onkeydown = (e) => {
            if (e.key === 'Escape' && state.get('isSearching')) {
                state.set('isSearching', false);
                state.set('searchResult', null);
            }
        };

        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.onclick = async () => {
                await api.auth.logout();
                state.set('user', null);
                state.set('files', []);
            };
        }

        const menuToggle = document.getElementById('mobile-menu-toggle');
        if (menuToggle) {
            menuToggle.onclick = () => {
                Sidebar.toggle(true);
            };
        }

        Sidebar.attachEvents();
        Explorer.attachEvents();
        AIInterface.attachEvents();
        StatusBar.attachEvents();
    }
}

window.app = new App();
