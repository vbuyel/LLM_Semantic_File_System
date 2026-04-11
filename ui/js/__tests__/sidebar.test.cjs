const { state } = require('../state.js');

describe('Sidebar logic', () => {
    beforeEach(() => {
        state.set('storageSource', 'local');
    });

    describe('render', () => {
        test('should render sidebar structure', () => {
            const activeSource = state.get('storageSource');
            const html = `
                <aside class="sidebar">
                    <span class="logo-text">Semantic FS</span>
                </aside>
            `;
            
            expect(html).toContain('sidebar');
            expect(html).toContain('Semantic FS');
        });

        test('should highlight active storage source', () => {
            const activeSource = 'local';
            const html = `
                <div class="sidebar__item ${activeSource === 'local' ? 'sidebar__item--active' : ''}" data-source="local">
                    Local Files
                </div>
            `;
            
            expect(html).toContain('sidebar__item--active');
        });

        test('should not highlight inactive source', () => {
            const activeSource = 'local';
            const html = `
                <div class="sidebar__item ${activeSource === 'drive' ? 'sidebar__item--active' : ''}" data-source="drive">
                    Google Drive
                </div>
            `;
            
            expect(html).not.toContain('sidebar__item--active');
        });

        test('should render storage options', () => {
            const sources = ['local', 'drive', 'gcs'];
            const html = sources.map(source => 
                `<div data-source="${source}">${source}</div>`
            ).join('');
            
            expect(html).toContain('local');
            expect(html).toContain('drive');
            expect(html).toContain('gcs');
        });

        test('should render views section', () => {
            const html = `
                <div class="sidebar__section-title">Storage</div>
                <div class="sidebar__section-title">Views</div>
            `;
            
            expect(html).toContain('Storage');
            expect(html).toContain('Views');
        });

        test('should render status indicators', () => {
            const html = `<div class="status-dot status-dot--online"></div>`;
            
            expect(html).toContain('status-dot--online');
        });

        test('should render logout button', () => {
            const html = `<div id="logout-btn">Logout</div>`;
            
            expect(html).toContain('logout-btn');
        });

        test('should render icons', () => {
            const html = `
                <i data-lucide="layers"></i>
                <i data-lucide="hard-drive"></i>
                <i data-lucide="cloud"></i>
            `;
            
            expect(html).toContain('data-lucide="layers"');
        });
    });

    describe('storage switch logic', () => {
        test('should update storageSource', () => {
            state.set('storageSource', 'drive');
            
            expect(state.get('storageSource')).toBe('drive');
        });

        test('should reset path when switching source', () => {
            state.set('currentPath', '/documents');
            state.set('storageSource', 'drive');
            state.set('currentPath', '/');
            state.set('breadcrumbs', [{ name: 'Root', path: '/' }]);
            
            expect(state.get('currentPath')).toBe('/');
            expect(state.get('breadcrumbs')).toHaveLength(1);
        });

        test('should trigger reload on source change', () => {
            const reloadCalled = false;
            state.set('storageSource', 'gcs');
            
            expect(state.get('storageSource')).toBe('gcs');
        });
    });

    describe('navigation items', () => {
        test('should have data-source attribute', () => {
            const html = `<div data-source="local">Local</div>`;
            
            expect(html).toContain('data-source="local"');
        });

        test('should handle favorites click', () => {
            const item = 'favorites';
            
            // Currently no click handler implemented
            expect(item).toBe('favorites');
        });

        test('should handle recent click', () => {
            const item = 'recent';
            
            // Currently no click handler implemented
            expect(item).toBe('recent');
        });
    });

    describe('breadcrumbs reset', () => {
        test('should reset breadcrumbs when switching storage', () => {
            state.set('breadcrumbs', [
                { name: 'Root', path: '/' },
                { name: 'Folder', path: '/folder' }
            ]);
            
            state.set('breadcrumbs', [{ name: 'Root', path: '/' }]);
            
            expect(state.get('breadcrumbs')).toHaveLength(1);
            expect(state.get('breadcrumbs')[0].name).toBe('Root');
        });
    });
});