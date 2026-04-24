const FILE_URL = 'http://localhost:8002';
const AI_URL = 'http://localhost:8003';


export const api = {
    auth: {
        async loginWithGoogle() {
            // Demo login - just sets a user in local storage
            const user = { id: '1', name: 'User', email: 'user@example.com' };
            localStorage.setItem('user', JSON.stringify(user));
            return user;
        },
        async logout() {
            localStorage.removeItem('user');
        },
        getUser() {
            try {
                const userStr = localStorage.getItem('user');
                return userStr ? JSON.parse(userStr) : null;
            } catch {
                return null;
            }
        }
    },
    files: {
        async uploadFile(file, path = '/') {
            const formData = new FormData();
            formData.append('file', file);

            const headers = {};
            const storageSource = state.get('storageSource');

            if (storageSource === 'drive') {
                headers['X-Auth-Provider'] = 'google';
                const user = JSON.parse(localStorage.getItem('user') || '{}');

                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }
            const res = await fetch(`${FILE_URL}/upload`, {
                method: 'POST',
                body: formData, headers
            });
            return res.json();
        },
    },
    ai: {
        async search(text, filePath = null) {
            let url = `${AI_URL}/ai_agent?text=${encodeURIComponent(text)}`;
            if (filePath) url += `&file_path=${encodeURIComponent(filePath)}`;
            const response = await fetch(url);
            return await response.json();
        }
    }
};
