import { api } from '../api.js';
import { state } from '../state.js';

export const Auth = {
    render() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="auth fade-in">
                <div class="auth__card">
                    <h1 class="auth__title">Semantic FS</h1>
                    <p class="auth__subtitle">Intelligence-first file management</p>
                    <button id="google-login" class="auth__google-btn">
                        <i data-lucide="layout"></i>
                        Sign in with Google
                    </button>
                </div>
            </div>
        `;
        
        lucide.createIcons();
        
        document.getElementById('google-login').onclick = async () => {
            const user = await api.auth.loginWithGoogle();
            state.set('user', user);
        };
    }
};
