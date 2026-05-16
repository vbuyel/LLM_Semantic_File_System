import { api } from '../../api.js';

let _initialized = false;
const _listeners = [];

export const Events = {
    init(owner) {
        if (!owner || _initialized) return;
        _initialized = true;

        api.events.connect(owner, (msg) => {
            if (msg.type !== 'events' || !msg.data) return;
            const data = msg.data;
            _listeners.forEach(fn => fn(data));
        });
    },

    subscribe(fn) {
        _listeners.push(fn);
        return () => {
            const idx = _listeners.indexOf(fn);
            if (idx !== -1) _listeners.splice(idx, 1);
        };
    },
};

export function createEventQueue(msType, fallbackText) {
    let _initialized = false;
    let _lastEventText = null;

    return {
        init(owner) {
            if (_initialized) return;
            _initialized = true;
            Events.init(owner);
            Events.subscribe((data) => {
                if (data.ms_type === msType) {
                    _lastEventText = data.event;
                }
            });
        },
        getLastEventText() {
            return _lastEventText || fallbackText;
        },
    };
}
