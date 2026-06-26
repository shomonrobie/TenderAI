// utils/api.js - API communication module
const CONFIG = {
    API_BASE_URL: 'http://localhost:5000/api',
    JWT_STORAGE_KEY: 'tenderai_jwt_token',
    USER_STORAGE_KEY: 'tenderai_user',
};

let DETECTED_API_URL = null;

const POSSIBLE_URLS = [
    CONFIG.API_BASE_URL,
    'https://itender-bd.streamlit.app/api',
    'http://localhost:5000/api',
    'http://127.0.0.1:5000/api',
];

async function getApiUrl() {
    if (DETECTED_API_URL) return DETECTED_API_URL;
    
    const result = await chrome.storage.local.get(['api_url']);
    if (result.api_url) {
        DETECTED_API_URL = result.api_url;
        return DETECTED_API_URL;
    }
    
    for (const url of POSSIBLE_URLS) {
        try {
            console.log('Testing API URL:', url);
            const response = await fetch(url + '/health', { method: 'HEAD', cache: 'no-cache' });
            if (response.ok) {
                DETECTED_API_URL = url;
                await chrome.storage.local.set({ 'api_url': url });
                console.log('✅ API URL detected:', url);
                return url;
            }
        } catch (e) {
            console.log('Failed:', url);
        }
    }
    
    DETECTED_API_URL = CONFIG.API_BASE_URL;
    return DETECTED_API_URL;
}

async function getAuthToken() {
    return new Promise((resolve, reject) => {
        chrome.storage.local.get([CONFIG.JWT_STORAGE_KEY], (result) => {
            const token = result[CONFIG.JWT_STORAGE_KEY];
            if (token) resolve(token);
            else reject(new Error('Not authenticated'));
        });
    });
}

async function login(username, password) {
    console.log('🔐 API: Login attempt for:', username);
    try {
        const apiUrl = await getApiUrl();
        const url = apiUrl + '/auth/login';
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const result = await response.json();
        if (result.success) {
            await chrome.storage.local.set({
                [CONFIG.JWT_STORAGE_KEY]: result.token,
                [CONFIG.USER_STORAGE_KEY]: result.user
            });
        }
        return result;
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function logout() {
    await chrome.storage.local.remove([CONFIG.JWT_STORAGE_KEY, CONFIG.USER_STORAGE_KEY]);
}