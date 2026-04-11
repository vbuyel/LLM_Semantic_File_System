export const state = {
    _data: {
        user: null,
        currentPath: '/',
        storageSource: 'local', // local, drive, gcs
        files: [],
        integrations: { googleDrive: 'idle', gcs: 'idle' },
        isLoading: false,
        isSearching: false,
        searchQuery: '',
        searchResult: null,
        activeView: 'grid', // grid or list
        breadcrumbs: [{ name: 'Root', path: '/' }]
    },
    _listeners: [],

    set(key, value) {
        this._data[key] = value;
        this._notify();
    },

    get(key) {
        return this._data[key];
    },

    update(updater) {
        updater(this._data);
        this._notify();
    },

    subscribe(listener) {
        this._listeners.push(listener);
        return () => {
            this._listeners = this._listeners.filter(l => l !== listener);
        };
    },

    _notify() {
        this._listeners.forEach(listener => listener(this._data));
    }
};
