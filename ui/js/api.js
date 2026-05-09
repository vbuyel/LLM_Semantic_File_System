import { state } from './state.js';

const GATEWAY_SERVER = 'http://localhost:8000';

export const api = {
    auth: {
        async loginWithGoogle(code, state) {
            const res = await fetch(`${GATEWAY_SERVER}/auth/google/callback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, state }),
            });
            if (!res.ok) {
                throw new Error('Google login failed');
            }
            const data = await res.json();
            const user = {
                id: data.user.sub || Date.now().toString(),
                name: data.user.name,
                email: data.user.email,
                picture: data.user.picture,
                accessToken: data.access_token,
            };
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

            if (storageSource === 'drive') {
                headers['X-Auth-Provider'] = 'google';
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }

            const res = await fetch(`${GATEWAY_SERVER}/gateway/get_objects?path=${encodeURIComponent(path)}`, {
                method: 'GET',
                headers,
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
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                headers['X-Owner-Email'] = user.email || '';
                headers['X-Auth-Provider'] = 'google';
                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }

            const res = await fetch(`${GATEWAY_SERVER}/gateway/upload_object`, {
                method: 'POST',
                body: formData,
                headers
            });
            return res.json();
        },
        async deleteFile(path) {
            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };
            const res = await fetch(`${GATEWAY_SERVER}/gateway/delete_object?path=${encodeURIComponent(path)}`, {
                method: 'DELETE',
                headers
            });
            if (!res.ok) throw new Error('Failed to delete file');
            return res.json();
        },
        async updateFile(file, path) {
            const formData = new FormData();
            formData.append('file', file);

            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };

            if (storageSource === 'drive') {
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                headers['X-Owner-Email'] = user.email || '';
                headers['X-Auth-Provider'] = 'google';
                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }

            const res = await fetch(`${GATEWAY_SERVER}/gateway/update_object?file_id=${encodeURIComponent(path)}`, {
                method: 'PUT',
                body: formData,
                headers
            });
            return res.json();
        },
        async downloadFile(path) {
            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };

            if (storageSource === 'drive') {
                headers['X-Auth-Provider'] = 'google';
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                if (user.accessToken) {
                    headers['Authorization'] = `Bearer ${user.accessToken}`;
                }
            }

            const res = await fetch(
                `${GATEWAY_SERVER}/gateway/download_object?path=${encodeURIComponent(path)}`,
                { method: 'GET', headers }
            );

            if (!res.ok) throw new Error('Download failed');

            // Extract filename from Content-Disposition header
            const disposition = res.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^"]+)"?/);
            const filename = match ? match[1] : path.split('/').pop();

            // Trigger browser save dialog
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            return filename;
        }
    },
    ai: {
        async search(text) {
            const response = await fetch(`${GATEWAY_SERVER}/gateway/ai_agent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            return await response.json();
        }
    }
};
