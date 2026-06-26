# _pages/extension_download.py - FIXED VERSION

import streamlit as st
import zipfile
import io
import json
import base64
from datetime import datetime

def show():
    """Extension Download Page - Only for registered users"""
    
    # Check if user is logged in
    if not st.session_state.get('logged_in', False):
        st.error("🔒 Please login to download the extension")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return
    
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Download TenderAI Chrome Extension</h1>
        <p>Auto-fill tender forms with your company data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user info
    user_id = st.session_state.user_id
    company_id = st.session_state.company_id
    username = st.session_state.username
    user_role = st.session_state.user_role
    
    # Get system configuration API URL
    api_url = get_system_api_url()
    
    # Show current configuration
    with st.expander("⚙️ Extension Configuration", expanded=False):
        st.info(f"📡 Extension will connect to: **{api_url}**")
        
        # Admin can override configuration
        if user_role in ['admin', 'system_admin']:
            st.markdown("---")
            st.markdown("### 🔧 Admin Configuration")
            
            new_api_url = st.text_input(
                "API Base URL", 
                value=api_url,
                help="The URL where the TenderAI backend is hosted"
            )
            
            if st.button("💾 Save Configuration", type="primary"):
                save_system_api_url(new_api_url)
                st.success("Configuration saved! New downloads will use this URL.")
                st.rerun()
            
            st.caption("Current users will need to re-download the extension to get the new URL.")
    
    # Create extension package
    extension_zip = create_extension_package(user_id, company_id, username, api_url, user_role)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 📥 Download Extension
        
        Click the button below to download the TenderAI Chrome Extension.
        
        **Features:**
        - 🔍 Automatically detects tender form fields
        - ✨ Auto-fills with your company data
        - 🎯 High confidence matches (90%+)
        - 🔒 Secure - never submits forms automatically
        - 📊 Tracks usage for your company
        - 🌐 Auto-detects your server URL
        
        **Installation Instructions:**
        1. Download the ZIP file
        2. Extract to a folder (keep it permanently)
        3. Open Chrome and go to `chrome://extensions/`
        4. Enable **"Developer mode"** (top right)
        5. Click **"Load unpacked"**
        6. Select the extracted folder
        7. Pin the extension for easy access
        """)
        
        # Download button
        st.download_button(
            label="📥 Download Extension (ZIP)",
            data=extension_zip,
            file_name=f"tenderai_extension_{company_id}_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
        
        # Log the download
        log_extension_download(user_id, company_id, username)
        
    with col2:
        st.markdown("""
        ### 🚀 Quick Setup
        
        1. **Download** the extension
        2. **Extract** the ZIP file
        3. **Install** in Chrome
        4. **Login** to TenderAI
        5. **Start** auto-filling forms!
        
        ### 💡 Tips
        
        - Keep the extension folder in a permanent location
        - The extension auto-detects your server URL
        - Update the extension when notified
        - Check your usage in the dashboard
        - Upgrade plan for more auto-fills
        """)
    
    # Show current usage
    st.markdown("---")
    st.markdown("### 📊 Your Current Usage")
    
    from database.unified_db_manager import UnifiedDatabaseManager
    db = UnifiedDatabaseManager()
    
    sub = db.get_company_subscription(company_id)
    plan = sub.get('plan', 'free')
    
    # Get current month usage
    conn = db.get_connection()
    cursor = conn.cursor()
    this_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_auto_fill_log'")
    if cursor.fetchone():
        cursor.execute("""
            SELECT COUNT(*) FROM extension_auto_fill_log 
            WHERE company_id = ? AND filled_at >= ?
        """, (company_id, this_month))
        used = cursor.fetchone()[0] or 0
    else:
        used = 0
    
    conn.close()
    
    plan_limits = {'free': 5, 'basic': 30, 'professional': 100, 'enterprise': -1}
    limit = plan_limits.get(plan, 5)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Your Plan", plan.upper())
    
    with col2:
        if limit == -1:
            st.metric("Auto-Fills Available", "Unlimited")
        else:
            remaining = max(0, limit - used)
            st.metric("Auto-Fills Available", f"{remaining} / {limit}")
    
    with col3:
        if limit != -1 and used >= limit:
            st.warning("⚠️ Limit reached! Upgrade for more.")
            if st.button("💳 Upgrade Plan"):
                st.session_state.page = "subscription"
                st.rerun()


def get_system_api_url():
    """Get the system-wide API URL configuration"""
    try:
        from database.unified_db_manager import db
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM system_config WHERE key = 'extension_api_url'")
        result = cursor.fetchone()
        
        if result and result[0]:
            api_url = result[0]
        else:
            import os
            if os.environ.get('STREAMLIT_SHARING') or os.environ.get('STREAMLIT_CLOUD'):
                api_url = "https://itender-bd.streamlit.app"
            else:
                api_url = "http://localhost:5000"
        
        conn.close()
        return api_url.rstrip('/')
        
    except Exception as e:
        print(f"Error getting API URL: {e}")
        return "http://localhost:5000"




def save_system_api_url(api_url):
    """Save the system-wide API URL configuration (admin only)"""
    try:
        from database.unified_db_manager import UnifiedDatabaseManager
        db = UnifiedDatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO system_config (key, value, updated_by)
            VALUES ('extension_api_url', ?, ?)
        """, (api_url.rstrip('/'), st.session_state.get('user_id')))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving API URL: {e}")
        return False

# In _pages/extension_download.py, replace the create_extension_package function

def create_extension_package(user_id, company_id, username, api_base_url, user_role):
    """Create a customized extension ZIP file with separate JS files"""
    
    zip_buffer = io.BytesIO()
    api_base_url = api_base_url.rstrip('/')
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # ========== MANIFEST.JSON ==========
        manifest = {
            "manifest_version": 3,
            "name": f"TenderAI Auto-Fill - {username}",
            "version": "1.0.1",
            "description": "AI-powered auto-fill for tender forms",
            "permissions": [
                "storage",
                "activeTab",
                "scripting",
                "webNavigation",
                "cookies",
                "notifications"
            ],
            "host_permissions": [
                f"{api_base_url}/*",
                "https://*.eptenders.gov.bd/*",
                "https://*.eprocure.gov.bd/*",
                "<all_urls>"
            ],           
            "action": {
                "default_popup": "popup.html",
                "default_title": "TenderAI Assistant",
                "default_icon": {
                    "16": "icons/icon16.png",
                    "32": "icons/icon32.png",
                    "48": "icons/icon48.png",
                    "128": "icons/icon128.png"
                }
            },
            "background": {
                "service_worker": "background.js",
                "type": "module"
            },
            "content_scripts": [
                {
                    "matches": ["<all_urls>"],
                    "js": ["content.js"],
                    "css": ["styles.css"],
                    "run_at": "document_end"
                }
            ],
            "web_accessible_resources": [
                {
                    "resources": ["icons/*", "styles.css", "utils/*"],
                    "matches": ["<all_urls>"]
                }
            ]
        }
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        
        # ========== UTILS/API.JS ==========
        api_js = f'''// utils/api.js - API communication module (ES Module)

const CONFIG = {{
    API_BASE_URL: '{api_base_url}/api',
    JWT_STORAGE_KEY: 'tenderai_jwt_token',
    USER_STORAGE_KEY: 'tenderai_user',
}};

// Store detected API URL
let DETECTED_API_URL = null;

// Possible API URLs to try
const POSSIBLE_URLS = [
    CONFIG.API_BASE_URL,
    'https://itender-bd.streamlit.app/api',
    'http://localhost:5000/api',
    'http://127.0.0.1:5000/api',
];

export async function getApiUrl() {{
    if (DETECTED_API_URL) return DETECTED_API_URL;
    
    const result = await chrome.storage.local.get(['api_url']);
    if (result.api_url) {{
        DETECTED_API_URL = result.api_url;
        return DETECTED_API_URL;
    }}
    
    for (const url of POSSIBLE_URLS) {{
        try {{
            console.log('Testing API URL:', url);
            const response = await fetch(url + '/health', {{ method: 'HEAD', cache: 'no-cache' }});
            if (response.ok) {{
                DETECTED_API_URL = url;
                await chrome.storage.local.set({{ 'api_url': url }});
                console.log('✅ API URL detected:', url);
                return url;
            }}
        }} catch (e) {{
            console.log('Failed:', url);
        }}
    }}
    
    DETECTED_API_URL = CONFIG.API_BASE_URL;
    return DETECTED_API_URL;
}}

export async function getAuthToken() {{
    return new Promise((resolve, reject) => {{
        chrome.storage.local.get([CONFIG.JWT_STORAGE_KEY], (result) => {{
            const token = result[CONFIG.JWT_STORAGE_KEY];
            if (token) resolve(token);
            else reject(new Error('Not authenticated'));
        }});
    }});
}}

export async function login(username, password) {{
    console.log('🔐 API: Login attempt for:', username);
    
    try {{
        const apiUrl = await getApiUrl();
        const url = apiUrl + '/auth/login';
        console.log('📡 API: Login URL:', url);
        
        const response = await fetch(url, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ username, password }})
        }});
        
        const result = await response.json();
        
        if (result.success) {{
            await chrome.storage.local.set({{
                [CONFIG.JWT_STORAGE_KEY]: result.token,
                [CONFIG.USER_STORAGE_KEY]: result.user
            }});
        }}
        return result;
        
    }} catch (error) {{
        console.error('Login error:', error);
        return {{ success: false, error: error.message }};
    }}
}}

export async function logout() {{
    await chrome.storage.local.remove([CONFIG.JWT_STORAGE_KEY, CONFIG.USER_STORAGE_KEY]);
}}

export async function getAutoFillData(dataType, searchTerm = null) {{
    const token = await getAuthToken();
    const apiUrl = await getApiUrl();
    let url = apiUrl + '/auto-fill/' + dataType;
    if (searchTerm) url += '?search=' + encodeURIComponent(searchTerm);
    
    const response = await fetch(url, {{
        headers: {{ 'Authorization': 'Bearer ' + token }}
    }});
    if (!response.ok) throw new Error('Failed to fetch data');
    return await response.json();
}}

export async function matchField(label, fieldType) {{
    const token = await getAuthToken();
    const apiUrl = await getApiUrl();
    const response = await fetch(apiUrl + '/match-field', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }},
        body: JSON.stringify({{ label, fieldType }})
    }});
    if (!response.ok) throw new Error('Match field failed');
    return await response.json();
}}

export async function getFillValue(source, field) {{
    const token = await getAuthToken();
    const apiUrl = await getApiUrl();
    const response = await fetch(apiUrl + '/get-fill-value', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }},
        body: JSON.stringify({{ source, field }})
    }});
    if (!response.ok) throw new Error('Get fill value failed');
    const result = await response.json();
    return result.value;
}}

export async function trackFormFill(data) {{
    const token = await getAuthToken();
    const apiUrl = await getApiUrl();
    try {{
        await fetch(apiUrl + '/track/form-fill', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            }},
            body: JSON.stringify(data)
        }});
    }} catch (error) {{
        console.error('Failed to track form fill:', error);
    }}
}}

export async function getUsageStats() {{
    const token = await getAuthToken();
    const apiUrl = await getApiUrl();
    try {{
        const response = await fetch(apiUrl + '/usage/stats', {{
            headers: {{ 'Authorization': 'Bearer ' + token }}
        }});
        return await response.json();
    }} catch (error) {{
        return {{ usage: {{ used: 0, limit: 5, remaining: 5 }} }};
    }}
}}

// Test connection on load
(async function testConnection() {{
    console.log('🔧 API: Testing connection...');
    const apiUrl = await getApiUrl();
    console.log('🔧 API: Using URL:', apiUrl);
    try {{
        const response = await fetch(apiUrl + '/health');
        if (response.ok) {{
            console.log('✅ API: Connection successful');
        }}
    }} catch (error) {{
        console.error('❌ API: Connection failed', error);
    }}
}})();
'''
        zipf.writestr("utils/api.js", api_js)
        
        # ========== UTILS/FIELDMATCHER.JS ==========
        field_matcher_js = '''// utils/fieldMatcher.js - Field matching module (ES Module)

const FIELD_PATTERNS = {
    'company_name': {
        keywords: ['company', 'firm', 'organization', 'contractor', 'name of firm', 'bidder name'],
        source: 'company_profile',
        field: 'company_name',
        confidence: 0.85
    },
    'tin_number': {
        keywords: ['tin', 'tax identification', 'tax id', 'tin number'],
        source: 'company_profile',
        field: 'tin_number',
        confidence: 0.90
    },
    'vat_number': {
        keywords: ['vat', 'value added tax', 'vat number', 'registration number'],
        source: 'company_profile',
        field: 'vat_number',
        confidence: 0.90
    },
    'phone': {
        keywords: ['phone', 'mobile', 'contact number', 'telephone', 'cell'],
        source: 'company_profile',
        field: 'phone',
        confidence: 0.85
    },
    'email': {
        keywords: ['email', 'e-mail', 'electronic mail'],
        source: 'company_profile',
        field: 'email',
        confidence: 0.95
    },
    'address': {
        keywords: ['address', 'office address', 'registered address', 'principal address'],
        source: 'company_profile',
        field: 'address',
        confidence: 0.80
    }
};

export function matchField(label, fieldType) {
    if (!label) return null;
    
    const labelLower = label.toLowerCase();
    
    for (const [fieldName, pattern] of Object.entries(FIELD_PATTERNS)) {
        for (const keyword of pattern.keywords) {
            if (labelLower.includes(keyword)) {
                return {
                    source: pattern.source,
                    field: pattern.field,
                    confidence: pattern.confidence
                };
            }
        }
    }
    
    return null;
}

export function getConfidenceLabel(confidence) {
    if (confidence >= 0.9) return 'High';
    if (confidence >= 0.7) return 'Medium';
    return 'Low';
}

'''
        zipf.writestr("utils/fieldMatcher.js", field_matcher_js)
        
        # ========== BACKGROUND.JS ==========
        background_js = '''// background.js - Main background service worker (ES Module)

// Import modules using ES6 import syntax
import { 
    getApiUrl, 
    getAuthToken, 
    login, 
    logout, 
    getAutoFillData, 
    matchField, 
    getFillValue, 
    trackFormFill,
    getUsageStats 
} from './utils/api.js';

import { matchField as matchFieldPattern } from './utils/fieldMatcher.js';

console.log('🚀 TenderAI Extension Background Service Worker Started (ES Module)');

// Settings management
let extensionSettings = {
    autoFillEnabled: true,
    confidenceThreshold: 0.7,
    showSuggestions: true,
    highlightFields: true
};

async function loadSettings() {
    const result = await chrome.storage.sync.get([
        'auto_fill_enabled', 
        'auto_fill_confidence', 
        'show_suggestions', 
        'highlight_fields'
    ]);
    extensionSettings = {
        autoFillEnabled: result.auto_fill_enabled !== false,
        confidenceThreshold: result.auto_fill_confidence || 0.7,
        showSuggestions: result.show_suggestions !== false,
        highlightFields: result.highlight_fields !== false
    };
}

async function saveSettings(settings) {
    const updates = {};
    if (settings.autoFillEnabled !== undefined) updates.auto_fill_enabled = settings.autoFillEnabled;
    if (settings.confidenceThreshold !== undefined) updates.auto_fill_confidence = settings.confidenceThreshold;
    if (settings.showSuggestions !== undefined) updates.show_suggestions = settings.showSuggestions;
    if (settings.highlightFields !== undefined) updates.highlight_fields = settings.highlightFields;
    await chrome.storage.sync.set(updates);
    extensionSettings = { ...extensionSettings, ...settings };
}

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('📨 Background received:', request.action);
    
    switch (request.action) {
        case 'getAuthToken':
            getAuthToken().then(token => sendResponse({ token: token }))
                .catch(error => sendResponse({ error: error.message }));
            return true;
            
        case 'login':
            login(request.data.username, request.data.password)
                .then(result => sendResponse(result));
            return true;
            
        case 'logout':
            logout().then(() => sendResponse({ success: true }));
            return true;
            
        case 'getAutoFillData':
            getAutoFillData(request.dataType, request.searchTerm)
                .then(data => sendResponse({ data: data }));
            return true;
            
        case 'matchField':
            const match = matchFieldPattern(request.label, request.fieldType);
            sendResponse({ match: match });
            return true;
            
        case 'getFillValue':
            getFillValue(request.source, request.field)
                .then(value => sendResponse({ value: value }));
            return true;
            
        case 'trackFormFill':
            trackFormFill(request.data).then(() => sendResponse({ success: true }));
            return true;
            
        case 'getSettings':
            sendResponse(extensionSettings);
            return true;
            
        case 'updateSettings':
            saveSettings(request.settings).then(() => sendResponse({ success: true }));
            return true;
            
        case 'getApiUrl':
            getApiUrl().then(url => sendResponse({ url: url }));
            return true;
            
        case 'getUsageStats':
            getUsageStats().then(stats => sendResponse(stats));
            return true;
    }
});

// Load settings on startup
loadSettings();
console.log('✅ Background service worker ready');

'''
        zipf.writestr("background.js", background_js)
        
        # ========== CONTENT.JS ==========
        content_js = '''// content.js - Content script for page analysis

let settings = { autoFillEnabled: true, confidenceThreshold: 0.7 };
let processedFields = new Set();

console.log('🎯 TenderAI Content Script Loaded');

// Load settings from background
async function loadSettings() {
    const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
    if (response) settings = { ...settings, ...response };
}

// Extract form fields from page
function extractFormFields() {
    const fields = [];
    const formElements = document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea'
    );
    
    for (const element of formElements) {
        if (element.value && element.value.trim() !== '') continue;
        
        fields.push({
            element: element,
            type: element.type || element.tagName.toLowerCase(),
            name: element.name || '',
            id: element.id || '',
            label: findLabel(element),
            placeholder: element.placeholder || ''
        });
    }
    return fields;
}

// Find associated label for an element
function findLabel(element) {
    if (element.id) {
        const label = document.querySelector(`label[for="${element.id}"]`);
        if (label) return label.textContent.trim();
    }
    
    let parent = element.parentElement;
    while (parent) {
        if (parent.tagName === 'LABEL') return parent.textContent.trim();
        parent = parent.parentElement;
    }
    
    return element.placeholder || element.name || '';
}

// Process a single field
async function processField(field) {
    const fieldId = field.id || field.name || field.label;
    if (processedFields.has(fieldId)) return;
    
    const label = field.label || field.placeholder || field.name;
    if (!label) return;
    
    try {
        const matchResult = await chrome.runtime.sendMessage({
            action: 'matchField',
            label: label,
            fieldType: field.type
        });
        
        if (matchResult && matchResult.match && 
            matchResult.match.confidence >= settings.confidenceThreshold) {
            
            const valueResult = await chrome.runtime.sendMessage({
                action: 'getFillValue',
                source: matchResult.match.source,
                field: matchResult.match.field
            });
            
            if (valueResult && valueResult.value) {
                fillField(field, valueResult.value);
                highlightField(field, matchResult.match.confidence);
                
                await chrome.runtime.sendMessage({
                    action: 'trackFormFill',
                    data: {
                        fieldType: field.type,
                        fieldLabel: label,
                        confidence: matchResult.match.confidence,
                        url: window.location.href
                    }
                });
                
                processedFields.add(fieldId);
            }
        }
    } catch (error) {
        console.error('Error processing field:', error);
    }
}

// Fill the field with value
function fillField(field, value) {
    field.element.value = value;
    field.element.dispatchEvent(new Event('input', { bubbles: true }));
    field.element.dispatchEvent(new Event('change', { bubbles: true }));
    field.element.dispatchEvent(new Event('blur', { bubbles: true }));
}

// Highlight filled field
function highlightField(field, confidence) {
    const originalBorder = field.element.style.border;
    const originalBg = field.element.style.backgroundColor;
    
    field.element.style.border = '2px solid #4CAF50';
    field.element.style.backgroundColor = '#e8f5e9';
    
    setTimeout(() => {
        field.element.style.border = originalBorder;
        field.element.style.backgroundColor = originalBg;
    }, 3000);
}

// Analyze all fields on page
async function analyzePage() {
    if (!settings.autoFillEnabled) return;
    
    const fields = extractFormFields();
    console.log(`Found ${fields.length} form fields`);
    
    for (const field of fields) {
        await processField(field);
    }
}

// Initialize and observe DOM changes
async function init() {
    await loadSettings();
    await analyzePage();
    
    // Observe for dynamically added forms
    const observer = new MutationObserver(async (mutations) => {
        let shouldAnalyze = false;
        for (const mutation of mutations) {
            if (mutation.type === 'childList' && mutation.addedNodes.length) {
                shouldAnalyze = true;
                break;
            }
        }
        if (shouldAnalyze) {
            setTimeout(analyzePage, 500);
        }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
}

// Start
init();
'''
        zipf.writestr("content.js", content_js)
        
        # ========== POPUP.HTML ==========
        popup_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { width: 360px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; text-align: center; }
        .header h3 { margin: 0; }
        .content { padding: 15px; }
        .status { padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-size: 13px; }
        .connected { background: #e8f5e9; color: #2e7d32; }
        .disconnected { background: #ffebee; color: #c62828; }
        .debug-info { font-size: 10px; color: #666; text-align: center; margin: 5px 0; word-break: break-all; }
        input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; }
        button { width: 100%; padding: 10px; margin: 8px 0; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-secondary { background: #e0e0e0; color: #333; }
        .btn-danger { background: #f44336; color: white; }
        .user-info { background: #f0f0f0; padding: 10px; border-radius: 8px; margin-bottom: 15px; text-align: center; }
        .footer { font-size: 10px; color: #999; text-align: center; padding: 10px; border-top: 1px solid #eee; }
        hr { margin: 10px 0; }
        .setting-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
        .setting-label { font-size: 13px; }
        .toggle { position: relative; width: 44px; height: 22px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: 0.3s; border-radius: 22px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 2px; bottom: 2px; background-color: white; transition: 0.3s; border-radius: 50%; }
        input:checked + .slider { background-color: #667eea; }
        input:checked + .slider:before { transform: translateX(22px); }
        .range-slider { width: 100%; margin-top: 5px; }
        .confidence-value { font-size: 12px; color: #667eea; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h3>🤖 TenderAI Assistant</h3>
    </div>
    <div class="content">
        <div id="apiStatus" class="debug-info"></div>
        <div id="status" class="status disconnected">Not logged in</div>
        
        <div id="loginSection">
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button id="loginBtn" class="btn-primary">Sign In</button>
            <button id="testApiBtn" class="btn-secondary">Test Connection</button>
        </div>
        
        <div id="userSection" style="display:none;">
            <div class="user-info">
                <div id="userName"></div>
                <div id="userPlan" style="font-size: 11px; margin-top: 5px;"></div>
            </div>
            <button id="logoutBtn" class="btn-danger">Sign Out</button>
            <hr>
            <div class="setting-item">
                <span class="setting-label">Auto-Fill Forms</span>
                <label class="toggle">
                    <input type="checkbox" id="autoFillToggle" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="setting-item">
                <span class="setting-label">Show Suggestions</span>
                <label class="toggle">
                    <input type="checkbox" id="suggestionsToggle" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="setting-item">
                <span class="setting-label">Highlight Fields</span>
                <label class="toggle">
                    <input type="checkbox" id="highlightToggle" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="setting-item">
                <span class="setting-label">Confidence Threshold</span>
                <div>
                    <input type="range" id="confidenceThreshold" min="0" max="100" step="5" class="range-slider">
                    <span id="confidenceValue" class="confidence-value">70%</span>
                </div>
            </div>
            <hr>
            <div id="usageInfo" style="font-size: 12px; color: #666; text-align: center;"></div>
        </div>
    </div>
    <div class="footer">TenderAI Auto-Fill Assistant v1.0</div>
    <script src="popup.js"></script>
</body>
</html>'''
        zipf.writestr("popup.html", popup_html)
        
        # ========== POPUP.JS ==========
        popup_js = '''// popup.js - Extension popup UI

let currentUser = null;

// Display API URL status
async function displayApiStatus() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getApiUrl' });
        if (response && response.url) {
            const apiDiv = document.getElementById('apiStatus');
            apiDiv.innerHTML = '🔗 ' + response.url;
            if (response.url.includes('5000')) {
                apiDiv.style.color = '#4CAF50';
            } else {
                apiDiv.style.color = '#FF9800';
            }
        }
    } catch(e) {
        console.log('Could not get API URL:', e);
    }
}

// Test API connection
async function testApiConnection() {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Testing connection...';
    
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getApiUrl' });
        const apiUrl = response.url;
        
        const testResponse = await fetch(apiUrl + '/health');
        if (testResponse.ok) {
            statusDiv.textContent = '✅ API connected!';
            statusDiv.className = 'status connected';
            setTimeout(() => {
                if (!currentUser) {
                    statusDiv.textContent = 'Not logged in';
                    statusDiv.className = 'status disconnected';
                }
            }, 2000);
        } else {
            statusDiv.textContent = '❌ API error: ' + testResponse.status;
            statusDiv.className = 'status disconnected';
        }
    } catch (error) {
        statusDiv.textContent = '❌ Cannot connect to API';
        statusDiv.className = 'status disconnected';
        console.error('API test failed:', error);
    }
}

// Login handler
document.getElementById('loginBtn')?.addEventListener('click', async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        alert('Please enter credentials');
        return;
    }
    
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Logging in...';
    
    try {
        const result = await chrome.runtime.sendMessage({
            action: 'login',
            data: { username, password }
        });
        
        if (result.success) {
            currentUser = result.user;
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('userSection').style.display = 'block';
            document.getElementById('userName').textContent = currentUser.full_name || currentUser.username;
            document.getElementById('userPlan').textContent = (currentUser.plan || 'Free').toUpperCase() + ' Plan';
            document.getElementById('status').className = 'status connected';
            document.getElementById('status').textContent = 'Connected';
            
            // Load usage stats
            loadUsageStats();
            displayApiStatus();
        } else {
            statusDiv.textContent = 'Login failed';
            statusDiv.className = 'status disconnected';
            alert('Login failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        statusDiv.textContent = 'Error';
        statusDiv.className = 'status disconnected';
        alert('Error: ' + error.message);
    }
});

// Logout handler
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await chrome.runtime.sendMessage({ action: 'logout' });
    currentUser = null;
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('userSection').style.display = 'none';
    document.getElementById('status').className = 'status disconnected';
    document.getElementById('status').textContent = 'Not logged in';
    displayApiStatus();
});

// Test connection button
document.getElementById('testApiBtn')?.addEventListener('click', testApiConnection);

// Settings toggles
document.getElementById('autoFillToggle')?.addEventListener('change', (e) => {
    chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: { autoFillEnabled: e.target.checked }
    });
});

document.getElementById('suggestionsToggle')?.addEventListener('change', (e) => {
    chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: { showSuggestions: e.target.checked }
    });
});

document.getElementById('highlightToggle')?.addEventListener('change', (e) => {
    chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: { highlightFields: e.target.checked }
    });
});

document.getElementById('confidenceThreshold')?.addEventListener('input', (e) => {
    const value = parseInt(e.target.value);
    document.getElementById('confidenceValue').textContent = value + '%';
    chrome.runtime.sendMessage({
        action: 'updateSettings',
        settings: { confidenceThreshold: value / 100 }
    });
});

// Load settings and usage
async function loadSettings() {
    const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
    if (response) {
        if (document.getElementById('autoFillToggle'))
            document.getElementById('autoFillToggle').checked = response.autoFillEnabled !== false;
        if (document.getElementById('suggestionsToggle'))
            document.getElementById('suggestionsToggle').checked = response.showSuggestions !== false;
        if (document.getElementById('highlightToggle'))
            document.getElementById('highlightToggle').checked = response.highlightFields !== false;
        if (document.getElementById('confidenceThreshold')) {
            const threshold = (response.confidenceThreshold || 0.7) * 100;
            document.getElementById('confidenceThreshold').value = threshold;
            document.getElementById('confidenceValue').textContent = Math.round(threshold) + '%';
        }
    }
}

async function loadUsageStats() {
    try {
        const stats = await chrome.runtime.sendMessage({ action: 'getUsageStats' });
        if (stats && stats.usage) {
            const usageInfo = document.getElementById('usageInfo');
            if (stats.usage.limit === -1) {
                usageInfo.innerHTML = '📊 Unlimited auto-fills available';
            } else {
                const remaining = stats.usage.limit - stats.usage.used;
                usageInfo.innerHTML = `📊 ${remaining} of ${stats.usage.limit} auto-fills remaining this month`;
            }
        }
    } catch(e) {
        console.log('Could not load usage stats');
    }
}

// Check if already logged in
async function checkAuth() {
    try {
        const tokenResponse = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
        if (tokenResponse.token) {
            const result = await chrome.storage.local.get(['tenderai_user']);
            if (result.tenderai_user) {
                currentUser = result.tenderai_user;
                document.getElementById('loginSection').style.display = 'none';
                document.getElementById('userSection').style.display = 'block';
                document.getElementById('userName').textContent = currentUser.full_name || currentUser.username;
                document.getElementById('userPlan').textContent = (currentUser.plan || 'Free').toUpperCase() + ' Plan';
                document.getElementById('status').className = 'status connected';
                document.getElementById('status').textContent = 'Connected';
                loadUsageStats();
            }
        }
    } catch(e) {
        console.log('Not authenticated');
    }
    displayApiStatus();
    loadSettings();
}

// Initialize
checkAuth();
'''
        zipf.writestr("popup.js", popup_js)
        
        # ========== STYLES.CSS ==========
        styles_css = '''/* styles.css - Extension styles */
.tenderai-suggestion {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    z-index: 10000;
    animation: fadeIn 0.2s ease;
}
.tenderai-suggestion-content {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 15px;
}
.tenderai-suggestion-label {
    color: #333;
    font-weight: 500;
    font-size: 13px;
}
.tenderai-apply-btn {
    background: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 12px;
    cursor: pointer;
}
.tenderai-dismiss-btn {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #999;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
}'''
        zipf.writestr("styles.css", styles_css)
        
        # ========== ICONS ==========
        icon_data = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADkSURBVFhH7ZdNCoMwEIXf7t17QHeg4k50J7oT3YlX0IVg/QkBc0w6kza1YqEPHjRMMu/LzCS1Hcdx/uEHYCsiIrYgSZIuiqI+BHmeT0RExF/OeZ4PAwzDsAXO8/xgGIYtiOM47vuf5/kUERGx+T3P8wIAKIrCAgCKomgBgKZpLAAwDEP7vq8FgGEYWgAAURTVpmk0AFAUBQBAXddj0zSa6rouMwyDgqZpmKIomLZtmWVZFgMAYBgGxjjnXBRFzDRNEwCAYRgmSRITAEAUxYyIgIhIgiRJYpZlGQCAMY4xJiIirrfHcZy/GAAql6fV1QVsyQAAAABJRU5ErkJggg=="
        
        for size in [16, 32, 48, 128]:
            zipf.writestr(f"icons/icon{size}.png", base64.b64decode(icon_data))
        
        # Create utils directory marker
        zipf.writestr("utils/.keep", "")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
def log_extension_download(user_id, company_id, username):
    """Log extension download for analytics"""
    try:
        from database.unified_db_manager import db
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO extension_downloads (user_id, company_id, username)
            VALUES (?, ?, ?)
        """, (user_id, company_id, username))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging download: {e}")
