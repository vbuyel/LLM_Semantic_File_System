import { state } from '../state.js';
import { api } from '../api.js';

// Completion events auto-dismiss after this many ms.
// Progress events persist until replaced by the next event.
const COMPLETION_CODES = new Set(['uploaded', 'updated', 'deleted', 'renamed', 'found']);

function _isCompletion(event) {
    if (COMPLETION_CODES.has(event)) return true;
    return /^(Done|Found|Complete|Error)/.test(event);
}

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

        if (_isCompletion(eventData.event)) {
            this._hideTimeout = setTimeout(() => {
                if (state.get('isSearching')) return;
                state.set('currentEvent', null);
            }, 2000);
        }
    },

    attachEvents() {
    }
};
