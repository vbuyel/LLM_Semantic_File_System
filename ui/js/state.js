export const state = {
    _data: {
        user: null,
        currentPath: '/',
        files: [],
        integrations: { googleDrive: 'idle', gcs: 'idle' },
        isSearching: false,
        activeView: 'grid' // grid or list
    },
    _listeners: [],

    set(key, value) {
        this._data[key] = value;
        this._notify();
    },

    get(key) {
        return this._data[key];
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
