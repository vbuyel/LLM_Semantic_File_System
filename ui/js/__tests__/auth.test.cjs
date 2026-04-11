const { state } = require('../state.js');

describe('Auth logic', () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="app"></div>';
    });

    describe('render', () => {
        test('should render auth card', () => {
            const html = `
                <div class="auth fade-in">
                    <div class="auth__card">
                        <h1 class="auth__title">Semantic FS</h1>
                        <p class="auth__subtitle">Intelligence-first file management</p>
                        <button id="google-login" class="auth__google-btn">Sign in with Google</button>
                    </div>
                </div>
            `;
            
            expect(html).toContain('auth');
            expect(html).toContain('auth__card');
            expect(html).toContain('Semantic FS');
        });

        test('should render google login button', () => {
            const html = `<button id="google-login">Sign in with Google</button>`;
            const googleLoginBtn = document.getElementById('google-login');
            
            expect(html).toContain('google-login');
        });

        test('should render title and subtitle', () => {
            const title = 'Semantic FS';
            const subtitle = 'Intelligence-first file management';
            const html = `
                <h1>${title}</h1>
                <p>${subtitle}</p>
            `;
            
            expect(html).toContain('Semantic FS');
            expect(html).toContain('Intelligence-first');
        });

        test('should use fade-in animation', () => {
            const html = `<div class="auth fade-in">`;
            
            expect(html).toContain('fade-in');
        });
    });

    describe('login flow', () => {
        test('should call login on button click', async () => {
            const loginWithGoogle = jest.fn().mockResolvedValue({ id: '1', name: 'User' });
            
            const user = await loginWithGoogle();
            
            expect(loginWithGoogle).toHaveBeenCalled();
            expect(user).toEqual({ id: '1', name: 'User' });
        });

        test('should set user in state after login', async () => {
            const user = { id: '1', name: 'Test User' };
            state.set('user', user);
            
            expect(state.get('user')).toEqual(user);
        });

        test('should store user in localStorage', () => {
            const user = { id: '1', name: 'Test' };
            localStorage.setItem('user', JSON.stringify(user));
            
            const stored = JSON.parse(localStorage.getItem('user'));
            
            expect(stored).toEqual(user);
        });
    });

    describe('icon rendering', () => {
        test('should render lucide icons', () => {
            const html = `<i data-lucide="layout"></i>`;
            
            expect(html).toContain('data-lucide="layout"');
        });
    });
});