const BASE_URL = 'http://localhost:8000';

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
        async getFiles(path = '/') {
            const response = await fetch(`${BASE_URL}/files?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error('Failed to fetch files');
            return await response.json();
        },
        async uploadFile(file, path = '/') {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`${BASE_URL}/files/upload?path=${encodeURIComponent(path)}`, {
                method: 'POST',
                body: formData
            });
            return await response.json();
        },
        async deleteFile(path) {
            const response = await fetch(`${BASE_URL}/files/delete`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
            return await response.json();
        },
        async rename(path, newName) {
            const response = await fetch(`${BASE_URL}/files/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, newName })
            });
            return await response.json();
        }
    },
    ai: {
        async search(text, filePath = null) {
            let url = `${BASE_URL}/ai_agent?text=${encodeURIComponent(text)}`;
            if (filePath) url += `&file_path=${encodeURIComponent(filePath)}`;
            const response = await fetch(url);
            return await response.json();
        }
    }
};
