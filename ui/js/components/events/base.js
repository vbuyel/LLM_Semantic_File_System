import { api } from '../../api.js';

let _initialized = false;
let _currentOwner = null;
let _ws = null;
const _listeners = [];

export const Events = {
    init(owner) {
        if (!owner || _initialized) return;
        _currentOwner = owner;
        _initialized = true;

        _ws = api.events.connect(owner, (msg) => {
            if (msg.type !== 'events' || !msg.data) return;
            const data = msg.data;
            _listeners.forEach(fn => fn(data));
        });
    },

    reconnect(owner) {
        if (!owner || owner === _currentOwner) return;
        _currentOwner = owner;
        if (_ws) {
            _ws.onclose = null;
            _ws.close();
            _ws = null;
        }
        _initialized = false;
        this.init(owner);
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
        reset() {
            _lastEventText = null;
        },
    };
}
