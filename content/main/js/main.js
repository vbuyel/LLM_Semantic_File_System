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
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const viewPanels = document.querySelectorAll('.view-panel');

    let currentQuery = '';
    let attachedFilePath = '';
    let currentFolderPath = '/';
    const favorites = new Set();

    function init() {
        setupEventListeners();
        loadApiEndpoint();
        setupFilesView();
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

        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                aiQueryInput.focus();
                aiQueryInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        const sidebarHeader = document.querySelector('.sidebar-header');
        if (sidebarHeader) {
            sidebarHeader.addEventListener('click', function() {
                switchView('search');
            });
            sidebarHeader.style.cursor = 'pointer';
        }

        navItems.forEach(item => {
            item.addEventListener('click', function() {
                const view = this.dataset.view;
                switchView(view);
            });
        });
    }

    function switchView(viewId) {
        navItems.forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewId);
        });

        viewPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === `view-${viewId}`);
        });

        if (viewId === 'search') {
            document.querySelector('.breadcrumb-item.current').textContent = 'Home';
        } else if (viewId === 'files' || viewId === 'favorites' || viewId === 'shared') {
            document.querySelector('.breadcrumb-item.current').textContent = 
                viewId.charAt(0).toUpperCase() + viewId.slice(1);
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

    function setupFilesView() {
        const filesGrid = document.querySelector('.files-grid');
        if (!filesGrid) return;

        filesGrid.addEventListener('dblclick', function(e) {
            const card = e.target.closest('.file-card');
            if (!card) return;

            if (card.classList.contains('folder')) {
                const folderName = card.querySelector('.file-name').textContent;
                currentFolderPath = currentFolderPath === '/' ? '/' + folderName : currentFolderPath + '/' + folderName;
                document.querySelector('.breadcrumb-item.current').textContent = folderName;
            }
        });

        filesGrid.addEventListener('click', function(e) {
            const card = e.target.closest('.file-card');
            if (!card) return;

            const deleteBtn = e.target.closest('.delete-btn');
            if (deleteBtn) {
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this item?')) {
                    card.remove();
                }
                return;
            }

            const favoriteBtn = e.target.closest('.favorite-btn');
            if (favoriteBtn) {
                e.stopPropagation();
                const fileName = card.querySelector('.file-name').textContent;
                toggleFavorite(fileName, card, favoriteBtn);
                return;
            }
        });

        const addButtonsContainer = document.querySelector('.files-view-header');
        if (!addButtonsContainer) {
            const filesView = document.getElementById('view-files');
            const header = document.createElement('div');
            header.className = 'files-view-header';
            header.innerHTML = `
                <button class="add-btn" id="add-folder-btn">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-1 8h-3v3h-2v-3h-3v-2h3V9h2v3h3v2z"/>
                    </svg>
                    New Folder
                </button>
                <button class="add-btn" id="add-file-btn">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 14h-3v3h-2v-3H8v-2h3v-3h2v3h3v2zm-3-7V3.5L18.5 9H13z"/>
                    </svg>
                    Add File
                </button>
                <input type="file" id="local-file-input" style="display: none;" multiple>
            `;
            filesView.insertBefore(header, filesGrid);
            
            const fileInput = document.getElementById('local-file-input');
            
            document.getElementById('add-folder-btn').addEventListener('click', async function() {
                if (window.showDirectoryPicker) {
                    try {
                        const dirHandle = await window.showDirectoryPicker();
                        addNewItem(dirHandle.name, 'folder');
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            alert('Error selecting folder: ' + err.message);
                        }
                    }
                } else {
                    const name = prompt('Enter folder name:');
                    if (name) {
                        addNewItem(name, 'folder');
                    }
                }
            });

            document.getElementById('add-file-btn').addEventListener('click', function() {
                fileInput.click();
            });

            fileInput.addEventListener('change', function(e) {
                for (const file of e.target.files) {
                    addNewItem(file.name, 'file');
                }
                fileInput.value = '';
            });
        }
    }

    function addNewItem(name, type) {
        const filesGrid = document.querySelector('.files-grid');
        const isFolder = type === 'folder';
        const color = isFolder ? '#FFC107' : '#4285F4';
        const iconPath = isFolder 
            ? 'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z'
            : 'M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z';

        const card = document.createElement('div');
        card.className = `file-card ${isFolder ? 'folder' : ''}`;
        card.innerHTML = `
            <div class="file-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="${color}">
                    <path d="${iconPath}"/>
                </svg>
            </div>
            <span class="file-name">${escapeHtml(name)}</span>
            <button class="favorite-btn" title="Add to favorites">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
                </svg>
            </button>
            <button class="delete-btn" title="Delete">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
            </button>
        `;
        filesGrid.appendChild(card);
    }

    function toggleFavorite(fileName, card, btn) {
        const svg = btn.querySelector('svg');
        if (favorites.has(fileName)) {
            favorites.delete(fileName);
            svg.setAttribute('fill', 'none');
        } else {
            favorites.add(fileName);
            svg.setAttribute('fill', '#FFC107');
        }
    }

    init();
})();
