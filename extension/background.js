// extension/background.js
// TenderAI Chrome Extension - Background Service Worker

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8501/api', // Update with production URL
    JWT_STORAGE_KEY: 'tenderai_jwt_token',
    USER_STORAGE_KEY: 'tenderai_user',
    AUTO_FILL_ENABLED_KEY: 'tenderai_auto_fill_enabled',
    CONFIDENCE_THRESHOLD: 0.7
};

// Initialize extension
chrome.runtime.onInstalled.addListener((details) => {
    console.log('TenderAI Extension installed', details.reason);
    
    // Set default settings
    chrome.storage.sync.set({
        [CONFIG.AUTO_FILL_ENABLED_KEY]: true,
        'auto_fill_confidence': CONFIG.CONFIDENCE_THRESHOLD,
        'show_suggestions': true,
        'highlight_fields': true
    });
    
    // Create notification if needed
    if (details.reason === 'install') {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: 'TenderAI Assistant Installed',
            message: 'Click the extension icon to log in and configure auto-fill settings.'
        });
    }
});

// Listen for authentication messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'getAuthToken':
            getAuthToken().then(token => {
                sendResponse({ token: token });
            }).catch(error => {
                sendResponse({ error: error.message });
            });
            return true;
            
        case 'login':
            handleLogin(request.data).then(result => {
                sendResponse(result);
            }).catch(error => {
                sendResponse({ success: false, error: error.message });
            });
            return true;
            
        case 'logout':
            handleLogout().then(() => {
                sendResponse({ success: true });
            });
            return true;
            
        case 'getAutoFillData':
            getAutoFillData(request.dataType, request.searchTerm).then(data => {
                sendResponse({ data: data });
            }).catch(error => {
                sendResponse({ error: error.message });
            });
            return true;
            
        case 'searchKnowledgeBase':
            searchKnowledgeBase(request.query, request.categories).then(results => {
                sendResponse({ results: results });
            }).catch(error => {
                sendResponse({ error: error.message });
            });
            return true;
            
        case 'getSettings':
            getSettings().then(settings => {
                sendResponse(settings);
            });
            return true;
            
        case 'updateSettings':
            updateSettings(request.settings).then(() => {
                sendResponse({ success: true });
            });
            return true;
            
        case 'trackFormFill':
            trackFormFill(request.data).then(() => {
                sendResponse({ success: true });
            });
            return true;
    }
});

// Authentication functions
async function getAuthToken() {
    return new Promise((resolve, reject) => {
        chrome.storage.local.get([CONFIG.JWT_STORAGE_KEY], (result) => {
            const token = result[CONFIG.JWT_STORAGE_KEY];
            if (token) {
                // Verify token is still valid
                verifyToken(token).then(isValid => {
                    if (isValid) {
                        resolve(token);
                    } else {
                        reject(new Error('Token expired'));
                    }
                }).catch(() => reject(new Error('Invalid token')));
            } else {
                reject(new Error('Not authenticated'));
            }
        });
    });
}

async function verifyToken(token) {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/verify-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}
async function getAutoFillData(dataType, searchTerm = null) {
    const token = await getAuthToken();
    
    let url = `${CONFIG.API_BASE_URL}/auto-fill/${dataType}`;
    if (searchTerm) {
        url += `?search=${encodeURIComponent(searchTerm)}`;
    }
    
    const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    // Handle limit exceeded
    if (response.status === 403) {
        const errorData = await response.json();
        if (errorData.error === 'limit_reached') {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon128.png',
                title: 'Auto-Fill Limit Reached',
                message: errorData.message || 'You have reached your monthly auto-fill limit. Upgrade to continue.',
                buttons: [{ title: 'Upgrade Plan' }]
            });
            throw new Error('LIMIT_REACHED');
        }
        throw new Error(errorData.message || 'Permission denied');
    }
    
    if (!response.ok) {
        throw new Error(`Failed to fetch ${dataType} data`);
    }
    
    const result = await response.json();
    
    // Update badge with remaining usage
    if (result.usage_remaining !== undefined) {
        updateBadge(result.usage_remaining);
    }
    
    return result.data;
}

// Add badge update function
function updateBadge(remaining) {
    if (remaining === -1) {
        chrome.action.setBadgeText({ text: '∞' });
        chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
    } else if (remaining <= 3 && remaining > 0) {
        chrome.action.setBadgeText({ text: remaining.toString() });
        chrome.action.setBadgeBackgroundColor({ color: '#FF9800' });
    } else if (remaining === 0) {
        chrome.action.setBadgeText({ text: '0' });
        chrome.action.setBadgeBackgroundColor({ color: '#F44336' });
    } else {
        chrome.action.setBadgeText({ text: '' });
    }
}

async function handleLogin(data) {
    console.log('🔧 BACKGROUND: handleLogin called');
    console.log('   Username:', data.username);
    
    try {
        console.log('🔧 STEP B1: Getting API URL...');
        const apiUrl = await getApiUrl();
        console.log('🔧 STEP B2: API URL is:', apiUrl);
        
        const url = apiUrl + '/api/auth/login';
        console.log('🔧 STEP B3: Full URL:', url);
        
        console.log('🔧 STEP B4: Sending fetch request...');
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: data.username, password: data.password })
        });
        
        console.log('🔧 STEP B5: Response status:', response.status);
        console.log('🔧 STEP B6: Response headers:', response.headers.get('content-type'));
        
        // Get response text first
        const responseText = await response.text();
        console.log('🔧 STEP B7: Response text (first 300 chars):', responseText.substring(0, 300));
        
        // Parse JSON
        let result;
        try {
            result = JSON.parse(responseText);
            console.log('🔧 STEP B8: Parsed JSON:', result);
        } catch (e) {
            console.error('🔧 STEP B8: JSON parse error:', e);
            console.log('Raw response that failed to parse:', responseText);
            return { success: false, error: 'Server returned invalid response. Expected JSON but got HTML. Make sure Flask API is running on port 5000.' };
        }
        
        if (!response.ok) {
            console.log('🔧 STEP B9: HTTP error:', response.status);
            return { success: false, error: result.message || 'Server error: ' + response.status };
        }
        
        if (result.success) {
            console.log('🔧 STEP B10: Login successful, saving token...');
            await chrome.storage.local.set({ 
                [CONFIG.JWT_STORAGE_KEY]: result.token, 
                [CONFIG.USER_STORAGE_KEY]: result.user 
            });
            console.log('🔧 STEP B11: Token saved');
            return { success: true, user: result.user };
        }
        
        console.log('🔧 STEP B12: Login failed:', result.message);
        return { success: false, error: result.message || 'Login failed' };
        
    } catch (error) {
        console.error('🔧 BACKGROUND ERROR:', error);
        return { success: false, error: error.message };
    }
}


async function handleLogout() {
    await chrome.storage.local.remove([CONFIG.JWT_STORAGE_KEY, CONFIG.USER_STORAGE_KEY]);
    notifyAllTabs('auth_changed', { isLoggedIn: false });
}

// API calls to TenderAI backend
async function getAutoFillData(dataType, searchTerm = null) {
    const token = await getAuthToken();
    
    let url = `${CONFIG.API_BASE_URL}/auto-fill/${dataType}`;
    if (searchTerm) {
        url += `?search=${encodeURIComponent(searchTerm)}`;
    }
    
    const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) {
        throw new Error(`Failed to fetch ${dataType} data`);
    }
    
    return await response.json();
}

async function searchKnowledgeBase(query, categories = null) {
    const token = await getAuthToken();
    
    const url = new URL(`${CONFIG.API_BASE_URL}/knowledge/search`);
    url.searchParams.append('q', query);
    if (categories && categories.length) {
        url.searchParams.append('categories', categories.join(','));
    }
    
    const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) {
        throw new Error('Search failed');
    }
    
    return await response.json();
}

// Settings management
async function getSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get([
            CONFIG.AUTO_FILL_ENABLED_KEY,
            'auto_fill_confidence',
            'show_suggestions',
            'highlight_fields'
        ], (result) => {
            resolve({
                autoFillEnabled: result[CONFIG.AUTO_FILL_ENABLED_KEY] !== false,
                confidenceThreshold: result.auto_fill_confidence || CONFIG.CONFIDENCE_THRESHOLD,
                showSuggestions: result.show_suggestions !== false,
                highlightFields: result.highlight_fields !== false
            });
        });
    });
}

async function updateSettings(settings) {
    const updates = {};
    if (settings.autoFillEnabled !== undefined) {
        updates[CONFIG.AUTO_FILL_ENABLED_KEY] = settings.autoFillEnabled;
    }
    if (settings.confidenceThreshold !== undefined) {
        updates.auto_fill_confidence = settings.confidenceThreshold;
    }
    if (settings.showSuggestions !== undefined) {
        updates.show_suggestions = settings.showSuggestions;
    }
    if (settings.highlightFields !== undefined) {
        updates.highlight_fields = settings.highlightFields;
    }
    
    return new Promise((resolve) => {
        chrome.storage.sync.set(updates, resolve);
    });
}

async function trackFormFill(data) {
    const token = await getAuthToken();
    
    try {
        await fetch(`${CONFIG.API_BASE_URL}/track/form-fill`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
    } catch (error) {
        console.error('Failed to track form fill:', error);
    }
}

// Helper functions
async function notifyAllTabs(action, data) {
    const tabs = await chrome.tabs.query({});
    for (const tab of tabs) {
        try {
            chrome.tabs.sendMessage(tab.id, { action, ...data });
        } catch (error) {
            // Ignore errors for tabs without content script
        }
    }
}

// Listen for tab updates to inject content script on relevant pages
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // Check if this is a tender-related page
        const tenderPatterns = [
            'tender', 'bid', 'proposal', 'procurement', 'eoi', 'rfp', 'rfq'
        ];
        
        const urlLower = tab.url.toLowerCase();
        const isTenderPage = tenderPatterns.some(pattern => urlLower.includes(pattern));
        
        if (isTenderPage) {
            // Inject content script if needed
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content.js']
            }).catch(() => {
                // Script already injected
            });
        }
    }
});