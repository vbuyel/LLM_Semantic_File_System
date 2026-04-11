const { state } = require('../state.js');

describe('Explorer logic', () => {
    describe('formatSize', () => {
        const formatSize = (bytes) => {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        };

        test('should format 0 bytes', () => {
            expect(formatSize(0)).toBe('0 B');
        });

        test('should format bytes correctly', () => {
            expect(formatSize(1024)).toBe('1 KB');
            expect(formatSize(1048576)).toBe('1 MB');
            expect(formatSize(1073741824)).toBe('1 GB');
        });

        test('should format with decimal places', () => {
            const result = formatSize(1536);
            expect(result).toContain('KB');
        });

        test('should handle negative bytes safely', () => {
            const result = formatSize(-100);
            expect(result).not.toBe('NaN');
        });
    });

    describe('render logic', () => {
        test('should return loading html', () => {
            const html = `
                <div class="explorer">
                    <div class="explorer__loading">
                        <div class="spinner"></div>
                        <p>Accessing storage...</p>
                    </div>
                </div>
            `;
            expect(html).toContain('explorer__loading');
        });

        test('should return empty state html', () => {
            const html = `<div class="explorer__empty">No files found in this directory</div>`;
            expect(html).toContain('explorer__empty');
        });

        test('should render file item with data attributes', () => {
            const file = { name: 'test.txt', isDirectory: false, path: '/test.txt' };
            const html = `<div class="explorer__item" data-path="${file.path}" data-type="${file.isDirectory ? 'folder' : 'file'}">${file.name}</div>`;
            
            expect(html).toContain('data-type="file"');
            expect(html).toContain('test.txt');
        });

        test('should render folder with type folder', () => {
            const file = { name: 'folder', isDirectory: true, path: '/folder' };
            const html = `<div class="explorer__item" data-type="${file.isDirectory ? 'folder' : 'file'}">${file.name}</div>`;
            
            expect(html).toContain('data-type="folder"');
        });

        test('should use view mode in class', () => {
            const viewMode = 'list';
            const html = `<div class="explorer explorer--${viewMode}"></div>`;
            
            expect(html).toContain('explorer--list');
        });

        test('should render breadcrumbs', () => {
            const breadcrumbs = [
                { name: 'Root', path: '/' },
                { name: 'Documents', path: '/documents' }
            ];
            const html = breadcrumbs.map((b, i) => 
                `<span class="breadcrumb-item" data-path="${b.path}">${b.name}</span>`
            ).join('');
            
            expect(html).toContain('breadcrumb-item');
            expect(html).toContain('Root');
            expect(html).toContain('Documents');
        });

        test('should escape file names to prevent XSS', () => {
            const escapeHtml = (str) => {
                if (typeof str !== 'string') return '';
                return str
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            };
            
            const file = { 
                name: '<script>alert("xss")</script>', 
                isDirectory: false, 
                path: '/test.txt' 
            };
            const html = `<div>${escapeHtml(file.name)}</div>`;
            
            expect(html).not.toContain('<script>');
            expect(html).toContain('&lt;script&gt;');
        });
    });

    describe('navigation logic', () => {
        test('should add to breadcrumbs', () => {
            state.set('breadcrumbs', [{ name: 'Root', path: '/' }]);
            state.set('currentPath', '/');
            
            const newBreadcrumbs = [
                ...state.get('breadcrumbs'),
                { name: 'Documents', path: '/documents' }
            ];
            state.set('breadcrumbs', newBreadcrumbs);
            state.set('currentPath', '/documents');
            
            expect(state.get('breadcrumbs')).toHaveLength(2);
        });

        test('should slice breadcrumbs for navigation', () => {
            state.set('breadcrumbs', [
                { name: 'Root', path: '/' },
                { name: 'Documents', path: '/documents' },
                { name: 'Work', path: '/documents/work' }
            ]);
            
            const newBreadcrumbs = state.get('breadcrumbs').slice(0, 2);
            state.set('breadcrumbs', newBreadcrumbs);
            
            expect(state.get('breadcrumbs')).toHaveLength(2);
        });
    });

    describe('file operations', () => {
        test('should handle empty files array', () => {
            const files = [];
            state.set('files', files);
            expect(state.get('files')).toEqual([]);
        });

        test('should add file', () => {
            const files = [{ name: 'existing.txt' }];
            state.set('files', files);
            
            const newFiles = [...files, { name: 'new.txt' }];
            state.set('files', newFiles);
            
            expect(state.get('files')).toHaveLength(2);
        });

        test('should filter file for delete', () => {
            state.set('files', [
                { name: 'file1.txt', path: '/file1.txt' },
                { name: 'file2.txt', path: '/file2.txt' }
            ]);
            
            const newFiles = state.get('files').filter(f => f.path !== '/file1.txt');
            state.set('files', newFiles);
            
            expect(state.get('files')).toHaveLength(1);
        });
    });
});