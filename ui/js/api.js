const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
    auth: {
        async loginWithGoogle() {
            await sleep(800);
            const user = { id: '1', name: 'Alex Rivera', email: 'alex@example.com' };
            localStorage.setItem('user', JSON.stringify(user));
            return user;
        },
        async logout() {
            localStorage.removeItem('user');
        },
        getUser() {
            return JSON.parse(localStorage.getItem('user'));
        }
    },
    files: {
        async getFiles(path = '/') {
            await sleep(400);
            return [
                { id: '1', name: 'Q4 Strategy.pdf', type: 'file', size: '2.4 MB', modified: '2024-03-10' },
                { id: '2', name: 'Design Assets', type: 'folder', size: '--', modified: '2024-03-08' },
                { id: '3', name: 'Research Notes.docx', type: 'file', size: '840 KB', modified: '2024-03-05' },
                { id: '4', name: 'Product Roadmap.xlsx', type: 'file', size: '1.2 MB', modified: '2024-03-01' },
                { id: '5', name: 'Interviews', type: 'folder', size: '--', modified: '2024-02-28' },
            ];
        },
        async search(query) {
            await sleep(600);
            // Simulated semantic search
            return [
                { id: '1', name: 'Q4 Strategy.pdf', relevance: 0.98 },
                { id: '4', name: 'Product Roadmap.xlsx', relevance: 0.85 }
            ];
        }
    },
    integrations: {
        async getStatus() {
            return {
                googleDrive: 'connected',
                gcs: 'connected'
            };
        }
    }
};
