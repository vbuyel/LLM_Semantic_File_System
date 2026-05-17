import { createEventQueue } from './base.js';

export const AIThinking = {
    ...createEventQueue('agent', 'Processing your request...'),

    render() {
        return `
            <div class="ai-thinking">
                <div class="thinking-dots"><span></span><span></span><span></span></div>
                <span>${this.getLastEventText()}</span>
            </div>
        `;
    },
};
