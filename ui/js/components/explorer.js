export const Explorer = {
    render(files) {
        if (!files || files.length === 0) {
            return `<div class="explorer">Loading files...</div>`;
        }

        const items = files.map(file => `
            <div class="explorer__item fade-in">
                <div class="explorer__icon">
                    <i data-lucide="${file.type === 'folder' ? 'folder' : 'file-text'}" size="32"></i>
                </div>
                <div class="explorer__name">${file.name}</div>
                <div style="font-size: 0.7rem; color: var(--text-muted)">${file.modified}</div>
            </div>
        `).join('');

        return `
            <div class="explorer">
                <div class="explorer__grid">
                    ${items}
                </div>
            </div>
        `;
    }
};
