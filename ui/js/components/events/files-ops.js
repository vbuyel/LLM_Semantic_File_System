import { createEventQueue } from './base.js';

export const FileOps = {
    ...createEventQueue('file_ops', 'Accessing storage...'),

    render() {
        return `
            <div class="explorer__loading">
                <div class="spinner"></div>
                <p>${this.getLastEventText()}</p>
            </div>
        `;
    },
};
