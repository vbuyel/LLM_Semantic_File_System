import { state } from '../state.js';
import { api } from '../api.js';

export const StatusBar = {
    _hideTimeout: null,

    render() {
        const currentEvent = state.get('currentEvent');
        if (!currentEvent) return '';
        return `
            <div class="status-bar fade-in">
                <div class="status-bar__content">
                    <div class="status-bar__spinner"></div>
                    <span class="status-bar__text">${api.events.getDisplayText(currentEvent.event)}</span>
                </div>
            </div>
        `;
    },

    showEvent(eventData) {
        if (state.get('isSearching')) return;
        state.set('currentEvent', eventData);
        if (this._hideTimeout) clearTimeout(this._hideTimeout);
        this._hideTimeout = setTimeout(() => {
            if (state.get('isSearching')) return;
            state.set('currentEvent', null);
        }, 3000);
    },

    attachEvents() {
    }
};
