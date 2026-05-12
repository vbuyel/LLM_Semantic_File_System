import { api } from '../api.js';
import { state } from '../state.js';

export const EventsPanel = {
    _ws: null,
    _events: [],

    async init(owner) {
        const data = await api.events.getUserEvents(owner, 50);
        this._events = data.events || [];
        state.set('events', this._events);
        state.subscribe((s) => {
            if (s.events) this._events = s.events;
        });

        this._ws = api.events.connect(owner, (msg) => {
            if (msg.type === 'events' && msg.data) {
                const current = state.get('events') || [];
                const newEvent = msg.data;
                const exists = current.some(e => e.id === newEvent.id);
                if (!exists) {
                    state.set('events', [newEvent, ...current].slice(0, 100));
                }
            }
        });
    },

    disconnect() {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
    },

    render() {
        const events = this._events;
        return `
            <div class="events-panel">
                <div class="events-panel__header">
                    <h3>Events</h3>
                    <span class="events-count">${events.length}</span>
                </div>
                <div class="events-panel__list">
                    ${events.length === 0 ? '<p class="events-empty">No events yet</p>' : ''}
                    ${events.map(e => `
                        <div class="event-item">
                            <span class="event-type">${e.event}</span>
                            <span class="event-time">${new Date(e.created_at).toLocaleString()}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    attachEvents() {
        const panel = document.querySelector('.events-panel');
        if (!panel) return;
    }
};