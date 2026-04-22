import { state } from '../state.js';
import { api } from '../api.js';

export const AIInterface = {
    render() {
        const isSearching = state.get('isSearching');
        const searchResult = state.get('searchResult');

        return `
            <div class="ai-bar-container">
                <div class="ai-bar fade-in">
                    <div class="ai-bar__input-wrapper">
                        <i data-lucide="sparkles" class="ai-sparkle"></i>
                        <input type="text" id="ai-search-input" class="ai-bar__input" 
                            placeholder="Find files by meaning: 'docs about marketing strategy'..."
                            value="${state.get('searchQuery') || ''}">
                        <kbd>Enter</kbd>
                    </div>
                </div>
                ${isSearching ? `
                    <div class="ai-thinking">
                        <div class="thinking-dots"><span></span><span></span><span></span></div>
                        <span>Agent is researching your files...</span>
                    </div>
                ` : ''}
                ${searchResult ? this.renderSearchResults(searchResult) : ''}
            </div>
        `;
    },

    renderSearchResults(result) {
        // Result is SearchResponse from backend
        const files = result.relevant_files || [];
        
        return `
            <div class="search-results fade-in">
                <div class="search-results__header">
                    <i data-lucide="search" size="14"></i>
                    <span>Semantic Search Results</span>
                    <button id="close-search" class="close-btn">&times;</button>
                </div>
                <div class="search-results__summary">${result.text || 'Found some relevant files:'}</div>
                <div class="search-results__list">
                    ${files.map(f => `
                        <div class="search-item" data-path="${f}">
                            <i data-lucide="file" size="14"></i>
                            <span>${f.split('/').pop()}</span>
                            <span class="search-item__path">${f}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    attachEvents() {
        const input = document.getElementById('ai-search-input');
        if (input) {
            input.onkeydown = async (e) => {
                if (e.key === 'Enter' && input.value.trim()) {
                    state.set('searchQuery', input.value);
                    state.set('isSearching', true);
                    state.set('searchResult', null);
                    
                    try {
                        const result = await api.ai.search(input.value);
                        state.set('searchResult', result);
                    } catch (error) {
                        console.error('AI Search failed:', error);
                    } finally {
                        state.set('isSearching', false);
                    }
                }
            };
        }

        const closeBtn = document.getElementById('close-search');
        if (closeBtn) {
            closeBtn.onclick = () => {
                state.set('searchResult', null);
                state.set('searchQuery', '');
            };
        }

        // Search item click (navigate to path)
        const searchItems = document.querySelectorAll('.search-item');
        searchItems.forEach(item => {
            item.onclick = () => {
                const path = item.dataset.path;
                // For now, just reset search and let user find it, 
                // but ideally we'd navigate to the folder
                state.set('searchResult', null);
                state.set('searchQuery', '');
            };
        });
    }
};
