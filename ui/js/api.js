import { state } from './state.js';
import { Events } from './components/events/base.js';

const GATEWAY_SERVER = 'http://localhost:8000';
const WS_SERVER = 'ws://localhost:8000';

function _getDriveHeaders() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const headers = {
        'X-Auth-Provider': 'google',
        'X-Owner': user.email || '',
    };
    if (user.accessToken) {
        headers['Authorization'] = `Bearer ${user.accessToken}`;
    }
    const corrId = Events.getCorrelationId();
    if (corrId) {
        headers['X-Correlation-ID'] = corrId;
    }
    return headers;
}

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

            if (storageSource === 'drive') Object.assign(headers, _getDriveHeaders());

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

            if (storageSource === 'drive') Object.assign(headers, _getDriveHeaders());

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
        async renameFile(oldPath, newName) {
            const storageSource = state.get('storageSource');
            const headers = { 
                'X-Storage-Source': storageSource,
                'Content-Type': 'application/json',
            };

            if (storageSource === 'drive') Object.assign(headers, _getDriveHeaders());

            const res = await fetch(`${GATEWAY_SERVER}/gateway/rename_object?path=${encodeURIComponent(oldPath)}&new_name=${encodeURIComponent(newName)}`, {
                method: 'PUT',
                headers
            });
            if (!res.ok) throw new Error('Failed to rename file');
            return res.json();
        },
        async downloadFile(path) {
            const storageSource = state.get('storageSource');
            const headers = { 'X-Storage-Source': storageSource };

            if (storageSource === 'drive') Object.assign(headers, _getDriveHeaders());

            const res = await fetch(
                `${GATEWAY_SERVER}/gateway/download_object?path=${encodeURIComponent(path)}`,
                { method: 'GET', headers }
            );

            if (!res.ok) throw new Error('Download failed');

            const disposition = res.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^"]+)"?/);
            const filename = match ? match[1] : path.split('/').pop();

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
    events: {
        getDisplayText(rawEvent) {
            if (!rawEvent) return "Processing...";
            return rawEvent.charAt(0).toUpperCase() + rawEvent.slice(1);
        },
        async getUserEvents(owner, ms_type, limit = 100, offset = 0) {
            const res = await fetch(
                `${GATEWAY_SERVER}/events/user/${encodeURIComponent(owner)}?ms_type=${ms_type}&limit=${limit}&offset=${offset}`
            );
            if (!res.ok) throw new Error('Failed to fetch events');
            return res.json();
        },
        connect(owner, onMessage) {
            let ws;

            function _connect() {
                ws = new WebSocket(`${WS_SERVER}/events/ws/${encodeURIComponent(owner)}`);

                ws.onmessage = (event) => {
                    try {
                        onMessage(JSON.parse(event.data));
                    } catch (e) {
                        console.error('[WS] Parse error:', e);
                    }
                };

                ws.onerror = (err) => console.error('[WS] Error:', err);

                ws.onopen = () => console.log('[WS] Connected:', owner);

                ws.onclose = () => {
                    console.log('[WS] Disconnected, reconnecting in 3s...');
                    setTimeout(_connect, 3000);
                };
            }

            _connect();
            return ws;
        }
    },
    ai: {
        async search(text) {
            const headers = { 'Content-Type': 'application/json' };
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            headers['X-Owner'] = user.email || user.id || 'guest';
            const corrId = Events.getCorrelationId();
            if (corrId) {
                headers['X-Correlation-ID'] = corrId;
            }

            const response = await fetch(`${GATEWAY_SERVER}/gateway/ai_agent`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ text }),
            });
            return await response.json();
        }
    }
};
