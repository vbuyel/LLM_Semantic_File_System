import { state } from '../state.js';
import { api } from '../api.js';

export const StatusBar = {
    _hideTimeout: null,

    render() {
        const currentEvent = state.get('currentEvent');
        
        if (!currentEvent) {
            return '';
        }

        const displayText = api.events.getDisplayText(currentEvent.event);
        
        return `
            <div class="status-bar fade-in">
                <div class="status-bar__content">
                    <div class="status-bar__spinner"></div>
                    <span class="status-bar__text">${displayText}</span>
                </div>
            </div>
        `;
    },

    attachEvents() {
    },

    showEvent(eventData) {
        state.set('currentEvent', eventData);
        
        if (this._hideTimeout) {
            clearTimeout(this._hideTimeout);
        }
        
        this._hideTimeout = setTimeout(() => {
            state.set('currentEvent', null);
        }, 3000);
    },

    init(userEmail) {
        if (!userEmail) return;
        
        api.events.connect(userEmail, (msg) => {
            if (msg.type === 'events' && msg.data) {
                this.showEvent(msg.data);
            }
        });
    }
};