import { createEventQueue } from './base.js';

export const AIThinking = {
    ...createEventQueue('agent', 'Agent is researching your files...'),

    render() {
        return `
            <div class="ai-thinking">
                <div class="thinking-dots"><span></span><span></span><span></span></div>
                <span>${this.getLastEventText()}</span>
            </div>
        `;
    },
};
