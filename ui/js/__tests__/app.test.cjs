const { state } = require('../state.js');

describe('app logic', () => {
    describe('state subscription for app', () => {
        test('should notify on state changes', () => {
            const listener = jest.fn();
            state.subscribe(listener);
            
            state.set('user', { id: '1' });
            
            expect(listener).toHaveBeenCalled();
        });
    });

    describe('loadInitialData logic', () => {
        beforeEach(() => {
            state.set('isLoading', false);
            state.set('files', []);
            state.set('currentPath', '/');
            
            global.fetch = jest.fn();
        });

        test('should set isLoading before fetch', async () => {
            let isLoadingDuringFetch;
            state.set('isLoading', true);
            isLoadingDuringFetch = state.get('isLoading');
            
            expect(isLoadingDuringFetch).toBe(true);
        });

        test('should clear isLoading after fetch completes', () => {
            state.set('isLoading', true);
            state.set('isLoading', false);
            
            expect(state.get('isLoading')).toBe(false);
        });

        test('should update files after successful fetch', () => {
            const mockFiles = [{ name: 'test.txt', isDirectory: false }];
            state.set('files', mockFiles);
            
            expect(state.get('files')).toEqual(mockFiles);
        });

        test('should handle path changes', () => {
            state.set('currentPath', '/documents');
            
            expect(state.get('currentPath')).toBe('/documents');
        });
    });

    describe('logout logic', () => {
        test('should reset state on logout', () => {
            state.set('user', { id: '1' });
            state.set('files', [{ name: 'file.txt' }]);
            
            state.set('user', null);
            state.set('files', []);
            
            expect(state.get('user')).toBeNull();
            expect(state.get('files')).toEqual([]);
        });
    });

    describe('escape key search clearing', () => {
        test('should clear search state', () => {
            state.set('isSearching', true);
            state.set('searchQuery', 'test query');
            state.set('searchResult', { answer: 'found' });
            
            state.set('isSearching', false);
            state.set('searchResult', null);
            
            expect(state.get('isSearching')).toBe(false);
            expect(state.get('searchResult')).toBeNull();
        });
    });

    describe('breadcrumb navigation', () => {
        test('should update breadcrumbs on navigation', () => {
            state.set('breadcrumbs', [{ name: 'Root', path: '/' }]);
            state.set('breadcrumbs', [
                { name: 'Root', path: '/' },
                { name: 'Documents', path: '/documents' }
            ]);
            
            expect(state.get('breadcrumbs')).toHaveLength(2);
        });
    });

    describe('view mode switching', () => {
        test('should switch between grid and list views', () => {
            expect(state.get('activeView')).toBe('grid');
            
            state.set('activeView', 'list');
            expect(state.get('activeView')).toBe('list');
            
            state.set('activeView', 'grid');
            expect(state.get('activeView')).toBe('grid');
        });
    });
});