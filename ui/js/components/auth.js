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
                            <h1 class="auth__title">Welcome Back</h1>
                            <p class="auth__subtitle">Sign in to manage your intelligent workspace</p>
                        </div>
                        
                        <div class="auth__tabs">
                            <button class="auth__tab active" id="tab-login">Login</button>
                            <button class="auth__tab" id="tab-register">Register</button>
                        </div>

                        <form id="auth-form" class="auth__form">
                            <div class="form-group" id="name-group" style="display: none;">
                                <label class="auth__label">Full Name</label>
                                <input type="text" id="auth-name" placeholder="John Doe" class="auth__input">
                            </div>
                            <div class="form-group">
                                <label class="auth__label">Email Address</label>
                                <input type="email" id="auth-email" placeholder="name@example.com" required class="auth__input">
                            </div>
                            <div class="form-group">
                                <label class="auth__label">Password</label>
                                <input type="password" id="auth-password" placeholder="••••••••" required class="auth__input">
                            </div>
                            <button type="submit" class="btn btn--primary auth__submit-btn" id="submit-btn">
                                Sign In
                            </button>
                        </form>

                        <div class="auth__divider">
                            <span>OR</span>
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
        
        let isLogin = true;
        const nameGroup = document.getElementById('name-group');
        const submitBtn = document.getElementById('submit-btn');
        const tabLogin = document.getElementById('tab-login');
        const tabRegister = document.getElementById('tab-register');
        const title = document.querySelector('.auth__title');
        const subtitle = document.querySelector('.auth__subtitle');

        const switchTab = (toLogin) => {
            isLogin = toLogin;
            nameGroup.style.display = isLogin ? 'none' : 'block';
            submitBtn.textContent = isLogin ? 'Sign In' : 'Create Account';
            title.textContent = isLogin ? 'Welcome Back' : 'Get Started';
            subtitle.textContent = isLogin ? 'Sign in to manage your intelligent workspace' : 'Create an account to unlock all features';
            
            tabLogin.classList.toggle('active', isLogin);
            tabRegister.classList.toggle('active', !isLogin);
        };

        tabLogin.onclick = () => switchTab(true);
        tabRegister.onclick = () => switchTab(false);
        
        document.getElementById('auth-form').onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('auth-email').value;
            const password = document.getElementById('auth-password').value;
            const name = isLogin ? 'Existing User' : document.getElementById('auth-name').value;
            
            const user = await api.auth.loginWithCredentials(name, email, password);
            state.set('user', user);
        };

        document.getElementById('google-login').onclick = () => {
            window.location.href = 'http://localhost:8000/auth/google/url';
        };

        document.getElementById('skip-login').onclick = async () => {
            const user = await api.auth.loginAsGuest();
            state.set('user', user);
        };
    }
};
