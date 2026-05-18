import { state } from '../state.js';
import { api } from '../api.js';
import { AIThinking } from './events/ai-thinking.js';

export const AIInterface = {
    render() {
        const isSearching = state.get('isSearching');
        const searchResult = state.get('searchResult');
        const user = state.get('user');

        let aiSearchScopeMessage = '';
        if (user) {
            if (user.isGuest) {
                aiSearchScopeMessage = "AI searches ONLY in Google Cloud Storage. AI can process ONLY human-readable files. File vectorization may take some time.";
            } else {
                aiSearchScopeMessage = "AI searches ONLY in Google Drive. AI can process ONLY human-readable files. File vectorization may take some time (depending on the number of files in Google Drive).";
            }
        }

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
                ${aiSearchScopeMessage ? `
                <div class="ai-bar__info-text fade-in">
                    <i data-lucide="info" size="12"></i>
                    <span>${aiSearchScopeMessage}</span>
                </div>` : ''}
                ${isSearching ? AIThinking.render() : ''}
                ${searchResult ? this.renderSearchResults(searchResult) : ''}
            </div>
        `;
    },

    renderSearchResults(result) {
        const files = result.relevant_files || [];
        const markdownHtml = result.text
            ? DOMPurify.sanitize(marked.parse(result.text))
            : 'Found some relevant files:';

        return `
            <div class="search-results fade-in">
                <div class="search-results__header">
                    <i data-lucide="search" size="14"></i>
                    <span>Semantic Search Results</span>
                    <button id="close-search" class="close-btn">&times;</button>
                </div>
                <div class="search-results__summary markdown-body">${markdownHtml}</div>
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
                    const query = input.value.trim();
                    AIThinking.reset();
                    state.update(data => {
                        data.searchQuery = query;
                        data.isSearching = true;
                        data.searchResult = null;
                    });
                    try {
                        const result = await api.ai.search(query);
                        state.update(data => {
                            data.searchResult = result;
                            data.isSearching = false;
                        });
                    } catch (error) {
                        console.error('AI Search failed:', error);
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

        const searchItems = document.querySelectorAll('.search-item');
        searchItems.forEach(item => {
            item.onclick = () => {
                const path = item.dataset.path;
                state.set('searchResult', null);
                state.set('searchQuery', '');
            };
        });
    }
};
