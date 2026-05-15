import { api } from '../api.js';

const _events = [];
let _initialized = false;
const _listeners = [];

export const AIThinking = {
    init(userEmail) {
        if (!userEmail || _initialized) return;
        _initialized = true;

        api.events.connect(userEmail, (msg) => {
            if (msg.type !== 'events' || !msg.data) return;
            const exists = _events.some(e => e.id === msg.data.id);
            if (exists) return;
            _events.unshift(msg.data);
            if (_events.length > 100) _events.length = 100;
            _listeners.forEach(fn => fn(msg.data));
        });
    },

    subscribe(fn) {
        _listeners.push(fn);
        return () => { _listeners.splice(_listeners.indexOf(fn), 1); };
    },

    getLastEventText() {
        const last = _events.pop(0);
        if (last && last.event) {
            return api.events.getDisplayText(last.event);
        }
        return 'Agent is researching your files...';
    },

    render() {
        return `
            <div class="ai-thinking">
                <div class="thinking-dots"><span></span><span></span><span></span></div>
                <span>${this.getLastEventText()}</span>
            </div>
        `;
    }
};
