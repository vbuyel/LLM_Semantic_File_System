(function() {
    const API_URL = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:8000/get_response';
    
    const aiQueryInput = document.getElementById('ai-query');
    const filePathInput = document.getElementById('file-path');
    const filePathSection = document.getElementById('file-path-section');
    const submitSearchBtn = document.getElementById('submit-search');
    const attachFileBtn = document.getElementById('attach-file');
    const clearFileBtn = document.getElementById('clear-file');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const resultsPanel = document.getElementById('results-panel');
    const resultsContent = document.getElementById('results-content');
    const resultCount = document.getElementById('result-count');
    const loadingState = document.getElementById('loading-state');
    const errorState = document.getElementById('error-state');
    const errorMessage = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');
    const globalSearch = document.getElementById('global-search');
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat');
    const chatMessages = document.getElementById('chat-messages');
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const viewPanels = document.querySelectorAll('.view-panel');

    let currentQuery = '';
    let attachedFilePath = '';

    function init() {
        setupEventListeners();
        loadApiEndpoint();
    }

    function setupEventListeners() {
        submitSearchBtn.addEventListener('click', performSearch);
        
        aiQueryInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        attachFileBtn.addEventListener('click', function() {
            filePathSection.style.display = filePathSection.style.display === 'none' ? 'flex' : 'none';
            if (filePathSection.style.display !== 'none') {
                filePathInput.focus();
            }
        });

        clearFileBtn.addEventListener('click', function() {
            filePathInput.value = '';
            attachedFilePath = '';
            filePathSection.style.display = 'none';
        });

        suggestionChips.forEach(chip => {
            chip.addEventListener('click', function() {
                aiQueryInput.value = this.dataset.query;
                aiQueryInput.focus();
            });
        });

        retryBtn.addEventListener('click', function() {
            hideError();
            performSearch();
        });

        globalSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                aiQueryInput.value = this.value;
                switchToSearchView();
                performSearch();
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'e') {
                e.preventDefault();
                aiQueryInput.focus();
            }
        });

        navItems.forEach(item => {
            item.addEventListener('click', function() {
                const view = this.dataset.view;
                switchView(view);
            });
        });

        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });

        sendChatBtn.addEventListener('click', sendChatMessage);
    }

    function switchView(viewId) {
        navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewId);
        });

        viewPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === `view-${viewId}`);
        });

        if (viewId === 'files' || viewId === 'recent' || viewId === 'favorites' || viewId === 'shared') {
            document.querySelector('.breadcrumb-item.current').textContent = 
                viewId.charAt(0).toUpperCase() + viewId.slice(1);
        } else if (viewId === 'search') {
            document.querySelector('.breadcrumb-item.current').textContent = 'Semantic Search';
        } else if (viewId === 'chat') {
            document.querySelector('.breadcrumb-item.current').textContent = 'AI Chat';
        } else if (viewId === 'settings') {
            document.querySelector('.breadcrumb-item.current').textContent = 'Settings';
        }
    }

    function switchToSearchView() {
        switchView('search');
    }

    function performSearch() {
        const query = aiQueryInput.value.trim();
        
        if (!query) {
            showError('Please enter a question');
            return;
        }

        currentQuery = query;
        attachedFilePath = filePathInput.value.trim();

        hideResults();
        showLoading();

        const payload = { text: query };
        
        if (attachedFilePath) {
            payload.file_path = attachedFilePath;
        }

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            if (data.text) {
                showResults(data.text);
            } else if (data.error) {
                showError(data.error);
            } else {
                showError('Unexpected response format');
            }
        })
        .catch(error => {
            hideLoading();
            let errorMsg = error.message;
            
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                errorMsg = 'Cannot connect to API. Is the server running at ' + API_URL + '?';
            }
            
            showError(errorMsg);
        });
    }

    function showResults(text) {
        resultsContent.textContent = text;
        resultCount.textContent = '1 result';
        resultsPanel.style.display = 'block';
    }

    function hideResults() {
        resultsPanel.style.display = 'none';
    }

    function showLoading() {
        loadingState.style.display = 'block';
    }

    function hideLoading() {
        loadingState.style.display = 'none';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorState.style.display = 'block';
    }

    function hideError() {
        errorState.style.display = 'none';
    }

    function sendChatMessage() {
        const message = chatInput.value.trim();
        
        if (!message) return;

        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user';
        userMessageDiv.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
            </div>
            <div class="message-content">${escapeHtml(message)}</div>
        `;
        
        chatMessages.appendChild(userMessageDiv);
        chatInput.value = '';

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot loading-message';
        loadingDiv.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                    <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
                </svg>
            </div>
            <div class="message-content">Thinking...</div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: message })
        })
        .then(response => response.json())
        .then(data => {
            chatMessages.removeChild(loadingDiv);
            
            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'message bot';
            botMessageDiv.innerHTML = `
                <div class="message-avatar">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                        <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
                    </svg>
                </div>
                <div class="message-content">${escapeHtml(data.text || 'No response')}</div>
            `;
            chatMessages.appendChild(botMessageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            chatMessages.removeChild(loadingDiv);
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message bot';
            errorDiv.innerHTML = `
                <div class="message-avatar">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="#f85149">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                </div>
                <div class="message-content" style="color: #f85149;">Error: ${escapeHtml(error.message)}</div>
            `;
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function loadApiEndpoint() {
        const stored = localStorage.getItem('apiEndpoint');
        if (stored) {
            const input = document.getElementById('api-endpoint');
            if (input) input.value = stored;
        }
    }

    document.getElementById('api-endpoint')?.addEventListener('change', function(e) {
        localStorage.setItem('apiEndpoint', e.target.value);
    });

    init();
})();
