const { state } = require('../state.js');

describe('state', () => {
    beforeEach(() => {
        state._data = {
            user: null,
            currentPath: '/',
            storageSource: 'local',
            files: [],
            integrations: { googleDrive: 'idle', gcs: 'idle' },
            isLoading: false,
            isSearching: false,
            searchQuery: '',
            searchResult: null,
            activeView: 'grid',
            breadcrumbs: [{ name: 'Root', path: '/' }]
        };
        state._listeners = [];
    });

    describe('set', () => {
        test('should set a value and notify listeners', () => {
            const listener = jest.fn();
            state.subscribe(listener);
            state.set('user', { id: '1', name: 'Test User' });
            
            expect(state.get('user')).toEqual({ id: '1', name: 'Test User' });
            expect(listener).toHaveBeenCalled();
        });

        test('should update nested properties correctly', () => {
            state.set('integrations', { googleDrive: 'connected', gcs: 'idle' });
            expect(state.get('integrations')).toEqual({ googleDrive: 'connected', gcs: 'idle' });
        });
    });

    describe('get', () => {
        test('should return default value for currentPath', () => {
            expect(state.get('currentPath')).toBe('/');
        });

        test('should return default value for storageSource', () => {
            expect(state.get('storageSource')).toBe('local');
        });

        test('should return undefined for non-existent key', () => {
            expect(state.get('nonExistent')).toBeUndefined();
        });
    });

    describe('update', () => {
        test('should update multiple values at once', () => {
            state.update((data) => {
                data.currentPath = '/documents';
                data.activeView = 'list';
            });
            
            expect(state.get('currentPath')).toBe('/documents');
            expect(state.get('activeView')).toBe('list');
        });

        test('should notify listeners after update', () => {
            const listener = jest.fn();
            state.subscribe(listener);
            state.update((data) => { data.isLoading = true; });
            
            expect(listener).toHaveBeenCalled();
        });
    });

    describe('subscribe', () => {
        test('should subscribe and receive notifications', () => {
            const listener = jest.fn();
            const unsubscribe = state.subscribe(listener);
            
            state.set('user', { id: '1' });
            expect(listener).toHaveBeenCalledTimes(1);
            
            unsubscribe();
            state.set('user', { id: '2' });
            expect(listener).toHaveBeenCalledTimes(1);
        });

        test('should return unsubscribe function', () => {
            const listener = jest.fn();
            const unsubscribe = state.subscribe(listener);
            
            expect(typeof unsubscribe).toBe('function');
            unsubscribe();
            state.set('user', null);
            expect(listener).not.toHaveBeenCalled();
        });
    });

    describe('breadcrumbs', () => {
        test('should initialize with Root breadcrumb', () => {
            const breadcrumbs = state.get('breadcrumbs');
            expect(breadcrumbs).toHaveLength(1);
            expect(breadcrumbs[0]).toEqual({ name: 'Root', path: '/' });
        });

        test('should update breadcrumbs correctly', () => {
            const newBreadcrumbs = [
                { name: 'Root', path: '/' },
                { name: 'Documents', path: '/documents' }
            ];
            state.set('breadcrumbs', newBreadcrumbs);
            expect(state.get('breadcrumbs')).toEqual(newBreadcrumbs);
        });
    });
});