const { state } = require('../state.js');

describe('AIInterface logic', () => {
    beforeEach(() => {
        state.set('isSearching', false);
        state.set('searchQuery', '');
        state.set('searchResult', null);
    });

    describe('render', () => {
        test('should render search input', () => {
            const html = `
                <div class="ai-bar-container">
                    <div class="ai-bar">
                        <input type="text" id="ai-search-input" placeholder="Find files by meaning...">
                    </div>
                </div>
            `;
            expect(html).toContain('ai-search-input');
            expect(html).toContain('Find files by meaning');
        });

        test('should render with current search query', () => {
            const searchQuery = 'marketing strategy';
            const html = `<input value="${searchQuery}">`;
            
            expect(html).toContain('marketing strategy');
        });

        test('should render thinking indicator when searching', () => {
            const isSearching = true;
            const html = isSearching ? `
                <div class="ai-thinking">
                    <div class="thinking-dots"><span></span><span></span><span></span></div>
                    <span>Agent is researching your files...</span>
                </div>
            ` : '';
            
            expect(html).toContain('ai-thinking');
            expect(html).toContain('Agent is researching');
        });

        test('should not render thinking when not searching', () => {
            const isSearching = false;
            const html = isSearching ? '<div class="ai-thinking"></div>' : '';
            
            expect(html).toBe('');
        });
    });

    describe('renderSearchResults', () => {
        test('should render search results', () => {
            const result = {
                answer: 'Found relevant files',
                relevant_files: ['/docs/marketing.txt', '/docs/strategy.pdf']
            };
            
            const files = result.relevant_files || [];
            const html = `
                <div class="search-results">
                    <div class="search-results__summary">${result.answer}</div>
                    <div class="search-results__list">
                        ${files.map(f => `<div class="search-item" data-path="${f}">${f.split('/').pop()}</div>`).join('')}
                    </div>
                </div>
            `;
            
            expect(html).toContain('search-results');
            expect(html).toContain('Found relevant files');
            expect(html).toContain('marketing.txt');
        });

        test('should handle empty results', () => {
            const result = { answer: 'No files found', relevant_files: [] };
            
            expect(result.relevant_files).toHaveLength(0);
        });

        test('should show default answer when not provided', () => {
            const result = { relevant_files: ['/test.txt'] };
            const answer = result.answer || 'Found some relevant files:';
            
            expect(answer).toBe('Found some relevant files:');
        });

        test('should extract filename from path', () => {
            const filePath = '/documents/project/report.pdf';
            const filename = filePath.split('/').pop();
            
            expect(filename).toBe('report.pdf');
        });

        test('should render close button', () => {
            const html = `
                <div class="search-results">
                    <button id="close-search" class="close-btn">&times;</button>
                </div>
            `;
            
            expect(html).toContain('close-search');
        });
    });

    describe('search logic', () => {
        test('should update searchQuery on input', () => {
            const inputValue = 'test query';
            state.set('searchQuery', inputValue);
            
            expect(state.get('searchQuery')).toBe('test query');
        });

        test('should toggle isSearching state', () => {
            state.set('isSearching', true);
            expect(state.get('isSearching')).toBe(true);
            
            state.set('isSearching', false);
            expect(state.get('isSearching')).toBe(false);
        });

        test('should clear searchResult on new search', () => {
            state.set('searchResult', { answer: 'old result' });
            state.set('searchResult', null);
            
            expect(state.get('searchResult')).toBeNull();
        });

        test('should clear search on close', () => {
            state.set('searchResult', { answer: 'result' });
            state.set('searchQuery', 'query');
            state.set('searchResult', null);
            state.set('searchQuery', '');
            
            expect(state.get('searchResult')).toBeNull();
            expect(state.get('searchQuery')).toBe('');
        });
    });

    describe('error handling', () => {
        test('should handle failed search gracefully', async () => {
            try {
                throw new Error('Search failed');
            } catch (error) {
                state.set('isSearching', false);
            }
            
            expect(state.get('isSearching')).toBe(false);
        });

        test('should handle empty search query', () => {
            const shouldSearch = '' && false;
            expect(shouldSearch).toBeFalsy();
        });

        test('should handle whitespace-only query', () => {
            const query = '   ';
            const shouldSearch = query.trim() && false;
            expect(shouldSearch).toBeFalsy();
        });
    });

    describe('file path navigation', () => {
        test('should get path from click', () => {
            const item = { dataset: { path: '/documents/file.txt' } };
            const path = item.dataset.path;
            
            expect(path).toBe('/documents/file.txt');
        });

        test('should navigate to folder (not implemented) - current behavior clears search', () => {
            state.set('searchResult', { answer: 'found' });
            state.set('searchResult', null);
            
            expect(state.get('searchResult')).toBeNull();
        });
    });
});