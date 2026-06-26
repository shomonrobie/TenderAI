// extension/popup.js
// TenderAI Assistant - Popup UI Controller

// DOM Elements
let loginView, mainView;
let statusBadge, userAvatar, userName, userEmail;
let autoFillToggle, suggestionsToggle, highlightToggle, confidenceSlider;
let searchInput, searchResults;
let analyzePageBtn, refreshDataBtn, logoutBtn;

// State
let isAuthenticated = false;
let currentUser = null;
let currentSettings = {};
let searchTimeout = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    loginView = document.getElementById('loginView');
    mainView = document.getElementById('mainView');
    statusBadge = document.getElementById('statusBadge');
    userAvatar = document.getElementById('userAvatar');
    userName = document.getElementById('userName');
    userEmail = document.getElementById('userEmail');
    autoFillToggle = document.getElementById('autoFillToggle');
    suggestionsToggle = document.getElementById('suggestionsToggle');
    highlightToggle = document.getElementById('highlightToggle');
    confidenceSlider = document.getElementById('confidenceThreshold');
    confidenceValue = document.getElementById('confidenceValue');
    searchInput = document.getElementById('searchInput');
    searchResults = document.getElementById('searchResults');
    analyzePageBtn = document.getElementById('analyzePageBtn');
    refreshDataBtn = document.getElementById('refreshDataBtn');
    logoutBtn = document.getElementById('logoutBtn');
    
    // Set up event listeners
    setupEventListeners();
    
    // Check authentication status
    checkAuthStatus();
    loadExtensionUsage();
    setupUpgradeListener();
    displayApiUrl();

    // Load settings
    loadSettings();
});

function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Settings toggles
    if (autoFillToggle) {
        autoFillToggle.addEventListener('change', (e) => {
            updateSetting('autoFillEnabled', e.target.checked);
        });
    }
    
    if (suggestionsToggle) {
        suggestionsToggle.addEventListener('change', (e) => {
            updateSetting('showSuggestions', e.target.checked);
        });
    }
    
    if (highlightToggle) {
        highlightToggle.addEventListener('change', (e) => {
            updateSetting('highlightFields', e.target.checked);
        });
    }
    
    if (confidenceSlider) {
        confidenceSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            confidenceValue.textContent = `${value}%`;
            updateSetting('confidenceThreshold', value / 100);
        });
    }
    
    // Search input with debounce
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            if (searchTimeout) clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 500);
        });
    }
    
    // Action buttons
    if (analyzePageBtn) {
        analyzePageBtn.addEventListener('click', () => {
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                chrome.tabs.sendMessage(tabs[0].id, { action: 'analyzePage' });
            });
        });
    }
    
    if (refreshDataBtn) {
        refreshDataBtn.addEventListener('click', refreshCompanyData);
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

async function checkAuthStatus() {
    try {
        const tokenResponse = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
        isAuthenticated = !!tokenResponse.token;
        
        if (isAuthenticated) {
            const userData = await chrome.storage.local.get(['tenderai_user']);
            currentUser = userData.tenderai_user;
            showMainView();
            loadStats();
        } else {
            showLoginView();
        }
    } catch (error) {
        showLoginView();
    }
}

function showLoginView() {
    loginView.style.display = 'block';
    mainView.style.display = 'none';
    statusBadge.textContent = 'Offline';
    statusBadge.className = 'status-badge disconnected';
}

async function displayApiUrl() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getApiUrl' });
        if (response && response.url) {
            const apiUrlDisplay = document.getElementById('apiUrlDisplay');
            if (apiUrlDisplay) {
                apiUrlDisplay.innerHTML = '🔗 API: ' + response.url;
                apiUrlDisplay.style.color = response.url.includes('5000') ? '#4CAF50' : '#FF9800';
            }
        }
    } catch(e) {
        console.log('Could not get API URL:', e);
    }
}

function showMainView() {
    loginView.style.display = 'none';
    mainView.style.display = 'block';
    statusBadge.textContent = 'Connected';
    statusBadge.className = 'status-badge connected';
    
    // Update user info
    if (currentUser) {
        userName.textContent = currentUser.full_name || currentUser.username;
        userEmail.textContent = currentUser.email;
        
        const initial = (currentUser.full_name || currentUser.username).charAt(0).toUpperCase();
        userAvatar.textContent = initial;
    }
}

async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');
    
    errorDiv.style.display = 'none';
    
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'login',
            data: { username, password }
        });
        
        if (response.success) {
            currentUser = response.user;
            showMainView();
            loadStats();
            loadSettings();
        } else {
            errorDiv.textContent = response.error || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Connection error. Please try again.';
        errorDiv.style.display = 'block';
    }
}
// Add test button handler
document.getElementById('testApiBtn')?.addEventListener('click', async () => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Testing API...';
    
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getApiUrl' });
        const apiUrl = response.url;
        
        statusDiv.textContent = 'Testing: ' + apiUrl;
        
        // Try to fetch health
        const fetchResult = await fetch(apiUrl + '/api/health');
        const data = await fetchResult.json();
        
        if (fetchResult.ok) {
            statusDiv.textContent = '✅ API OK! Server: ' + apiUrl;
            statusDiv.className = 'status connected';
            document.getElementById('apiUrlDisplay').innerHTML = '✅ Connected to: ' + apiUrl;
        } else {
            statusDiv.textContent = '❌ API Error: ' + fetchResult.status;
            statusDiv.className = 'status disconnected';
        }
    } catch (error) {
        statusDiv.textContent = '❌ Connection failed: ' + error.message;
        statusDiv.className = 'status disconnected';
        console.error('Test failed:', error);
    }
});
async function handleLogout() {
    await chrome.runtime.sendMessage({ action: 'logout' });
    isAuthenticated = false;
    currentUser = null;
    showLoginView();
}

async function loadSettings() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
        currentSettings = response;
        
        // Update UI
        if (autoFillToggle) autoFillToggle.checked = currentSettings.autoFillEnabled !== false;
        if (suggestionsToggle) suggestionsToggle.checked = currentSettings.showSuggestions !== false;
        if (highlightToggle) highlightToggle.checked = currentSettings.highlightFields !== false;
        
        const threshold = (currentSettings.confidenceThreshold || 0.7) * 100;
        if (confidenceSlider) confidenceSlider.value = threshold;
        if (confidenceValue) confidenceValue.textContent = `${Math.round(threshold)}%`;
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}
async function loadExtensionUsage() {
    try {
        const tokenResponse = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
        if (!tokenResponse.token) return;
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/usage/stats`, {
            headers: { 'Authorization': `Bearer ${tokenResponse.token}` }
        });
        
        const data = await response.json();
        
        if (data.usage) {
            const { used, limit, remaining } = data.usage;
            const usageUsedElem = document.getElementById('usageUsed');
            const usageLimitElem = document.getElementById('usageLimit');
            const usageFillElem = document.getElementById('usageFill');
            const upgradeMessageElem = document.getElementById('upgradeMessage');
            
            if (usageUsedElem) usageUsedElem.textContent = used;
            if (usageLimitElem) usageLimitElem.textContent = limit === -1 ? '∞' : limit;
            
            if (usageFillElem && limit !== -1) {
                const percent = Math.min(100, (used / limit) * 100);
                usageFillElem.style.width = `${percent}%`;
                
                // Change color based on usage
                if (percent >= 90) {
                    usageFillElem.style.background = '#f44336';
                } else if (percent >= 75) {
                    usageFillElem.style.background = '#ff9800';
                }
            }
            
            if (upgradeMessageElem && remaining === 0 && limit !== -1) {
                upgradeMessageElem.style.display = 'block';
            } else if (upgradeMessageElem) {
                upgradeMessageElem.style.display = 'none';
            }
        }
        
        // Update plan info display
        if (data.plan_name) {
            const planElem = document.getElementById('currentPlan');
            if (planElem) planElem.textContent = data.plan_name;
        }
        
    } catch (error) {
        console.error('Failed to load extension usage:', error);
    }
}

// Add upgrade link handler
function setupUpgradeListener() {
    const upgradeLink = document.getElementById('upgradeLink');
    if (upgradeLink) {
        upgradeLink.addEventListener('click', (e) => {
            e.preventDefault();
            chrome.tabs.create({ url: 'http://localhost:8501/?page=subscription' });
        });
    }
}


async function updateSetting(key, value) {
    currentSettings[key] = value;
    await chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: { [key]: value }
    });
}

async function performSearch(query) {
    if (!query.trim()) {
        searchResults.innerHTML = '<div class="loading">Enter a search term...</div>';
        return;
    }
    
    const loadingDiv = document.getElementById('searchLoading');
    if (loadingDiv) loadingDiv.style.display = 'block';
    
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'searchKnowledgeBase',
            query: query,
            categories: ['personnel', 'equipment', 'experience', 'financial']
        });
        
        displaySearchResults(response.results);
        
    } catch (error) {
        searchResults.innerHTML = `<div class="error-message">Search failed: ${error.message}</div>`;
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}

function displaySearchResults(results) {
    if (!results || results.length === 0) {
        searchResults.innerHTML = '<div class="loading">No results found</div>';
        return;
    }
    
    const resultsHtml = results.map(result => {
        let icon = '📄';
        let badge = result.source;
        
        switch (result.source) {
            case 'personnel':
                icon = '👤';
                badge = 'Personnel';
                break;
            case 'equipment':
                icon = '🏗️';
                badge = 'Equipment';
                break;
            case 'experience':
                icon = '📋';
                badge = 'Experience';
                break;
            case 'financial':
                icon = '💰';
                badge = 'Financial';
                break;
        }
        
        return `
            <div class="search-result-item" data-source="${result.source}" data-id="${result.id}">
                <div class="result-title">${icon} ${escapeHtml(result.name)}</div>
                <div class="result-subtitle">${escapeHtml(result.designation || result.type || result.client || '')}</div>
                <span class="result-badge">${badge}</span>
            </div>
        `;
    }).join('');
    
    searchResults.innerHTML = resultsHtml;
    
    // Add click handlers
    document.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const source = item.dataset.source;
            const id = item.dataset.id;
            viewItemDetails(source, id);
        });
    });
}

async function viewItemDetails(source, id) {
    // Implementation to show details in a modal or new tab
    console.log('View details:', source, id);
    // Could open a new tab with the company dashboard showing the item
}

async function loadStats() {
    try {
        const response = await chrome.storage.local.get(['tenderai_stats']);
        const stats = response.tenderai_stats || { fills: 0, totalConfidence: 0, count: 0 };
        
        const fillCountElem = document.getElementById('fillCount');
        const confidenceAvgElem = document.getElementById('confidenceAvg');
        const timeSavedElem = document.getElementById('timeSaved');
        
        if (fillCountElem) fillCountElem.textContent = stats.fills || 0;
        
        const avgConfidence = stats.count > 0 ? Math.round((stats.totalConfidence / stats.count) * 100) : 0;
        if (confidenceAvgElem) confidenceAvgElem.textContent = `${avgConfidence}%`;
        
        // Estimate time saved: 5 seconds per fill
        const timeSaved = Math.round(((stats.fills || 0) * 5) / 60);
        if (timeSavedElem) timeSavedElem.textContent = timeSaved;
        
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function refreshCompanyData() {
    const loadingDiv = document.getElementById('searchLoading');
    if (loadingDiv) loadingDiv.style.display = 'block';
    
    try {
        await chrome.runtime.sendMessage({ action: 'refreshCompanyData' });
        showTemporaryMessage('success', 'Company data refreshed successfully!');
        
        // Clear search and refresh if there's a query
        if (searchInput.value.trim()) {
            performSearch(searchInput.value);
        }
    } catch (error) {
        showTemporaryMessage('error', `Failed to refresh: ${error.message}`);
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}

function showTemporaryMessage(type, message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'success' ? 'success-message' : 'error-message';
    messageDiv.textContent = message;
    
    const container = document.querySelector('.content');
    container.insertBefore(messageDiv, container.firstChild);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}