import { state } from './state.js';

const FILE_URL = 'http://localhost:8002';
const AI_URL = 'http://localhost:8003';

export const api = {
    auth: {
        async loginWithGoogle() {
            const user = { id: 'google_1', name: 'Google User', email: 'google@example.com' };
            localStorage.setItem('user', JSON.stringify(user));
            return user;
        },
        async loginWithCredentials(name, email, password) {
            const user = { id: Date.now().toString(), name, email };
            localStorage.setItem('user', JSON.stringify(user));
            return user;
        },
        async loginAsGuest() {
            const user = { id: 'guest', name: 'Guest', isGuest: true };
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
        async getFiles(path = '/') {
            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };
            const res = await fetch(`${FILE_URL}/files?path=${encodeURIComponent(path)}`, {
                method: 'GET',
                headers
            });
            if (!res.ok) throw new Error('Failed to list files');
            const data = await res.json();
            return data.files || [];
        },
        async uploadFile(file, path = '/') {
            const formData = new FormData();
            formData.append('file', file);

            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };

            if (storageSource === 'drive') {
                headers['X-Auth-Provider'] = 'google';
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }
            const res = await fetch(`${FILE_URL}/upload`, {
                method: 'POST',
                body: formData,
                headers
            });
            return res.json();
        },
        async deleteFile(path) {
            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };
            const res = await fetch(`${FILE_URL}/delete?path=${encodeURIComponent(path)}`, {
                method: 'DELETE',
                headers
            });
            if (!res.ok) throw new Error('Failed to delete file');
            return res.json();
        }
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
