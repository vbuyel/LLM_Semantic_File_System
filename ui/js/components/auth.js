import { api } from '../api.js';
import { state } from '../state.js';

export const Auth = {
    render() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="auth fade-in">
                <div class="auth__container">
                    <div class="auth__visual">
                        <div class="auth__visual-content">
                            <div class="auth__visual-logo">
                                <i data-lucide="folder-search" size="48"></i>
                            </div>
                            <h2 class="auth__visual-title">Semantic File System</h2>
                            <p class="auth__visual-text">Experience the future of file management with AI-driven semantics and seamless cloud integration.</p>
                            <div class="auth__visual-features">
                                <div class="feature-tag"><i data-lucide="zap" size="14"></i> AI Powered</div>
                                <div class="feature-tag"><i data-lucide="shield" size="14"></i> Secure</div>
                                <div class="feature-tag"><i data-lucide="cloud" size="14"></i> Multi-cloud</div>
                            </div>
                        </div>
                        <div class="auth__visual-blobs">
                            <div class="blob"></div>
                            <div class="blob"></div>
                        </div>
                    </div>
                    
                    <div class="auth__card">
                        <div class="auth__header">
                            <h1 class="auth__title">Welcome</h1>
                            <p class="auth__subtitle">Sign in to manage your intelligent workspace</p>
                        </div>

                        <button id="google-login" class="auth__google-btn">
                            <i data-lucide="log-in"></i>
                            Sign in with Google
                        </button>

                        <button id="skip-login" class="auth__skip-btn">
                            Continue as Guest
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        lucide.createIcons();
        
        document.getElementById('google-login').onclick = () => {
            window.location.href = 'http://localhost:8000/auth/google/url';
        };

        document.getElementById('skip-login').onclick = async () => {
            const user = await api.auth.loginAsGuest();
            state.set('user', user);
        };
    }
};
