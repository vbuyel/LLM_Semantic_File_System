export const AIInterface = {
    render() {
        return `
            <div class="ai-bar fade-in">
                <div class="ai-bar__input-wrapper">
                    <i data-lucide="sparkles" style="color: var(--accent); width: 18px"></i>
                    <input type="text" class="ai-bar__input" placeholder="Search semantically: 'find strategy docs from last month'...">
                    <kbd style="background: var(--bg-primary); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; border: 1px solid var(--border-color)">⌘ K</kbd>
                </div>
            </div>
        `;
    }
};
