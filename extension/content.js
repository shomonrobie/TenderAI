// extension/content.js
// TenderAI Auto-Fill Assistant - Content Script

// Global state
let isAuthenticated = false;
let currentUser = null;
let settings = {
    autoFillEnabled: true,
    confidenceThreshold: 0.7,
    showSuggestions: true,
    highlightFields: true
};

let highlightedFields = [];
let suggestionBoxes = [];

// Initialize when page loads
(function init() {
    console.log('TenderAI Assistant initialized');
    
    // Load settings
    loadSettings();
    
    // Check authentication status
    checkAuthStatus();
    
    // Listen for messages from background
    chrome.runtime.onMessage.addListener(handleMessage);
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', analyzePage);
    } else {
        analyzePage();
    }
    
    // Observe DOM changes for dynamic forms
    observeDOMChanges();
})();

async function loadSettings() {
    const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
    if (response) {
        settings = { ...settings, ...response };
    }
}

async function checkAuthStatus() {
    try {
        const tokenResponse = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
        isAuthenticated = !!tokenResponse.token;
        
        if (isAuthenticated) {
            const userData = await chrome.storage.local.get(['tenderai_user']);
            currentUser = userData.tenderai_user;
        }
    } catch (error) {
        isAuthenticated = false;
        currentUser = null;
    }
}

function handleMessage(request, sender, sendResponse) {
    switch (request.action) {
        case 'auth_changed':
            isAuthenticated = request.isLoggedIn;
            currentUser = request.user;
            if (isAuthenticated) {
                analyzePage();
            } else {
                clearAllHighlights();
            }
            break;
            
        case 'settings_updated':
            loadSettings().then(() => {
                if (settings.autoFillEnabled && isAuthenticated) {
                    analyzePage();
                } else {
                    clearAllHighlights();
                }
            });
            break;
            
        case 'manual_fill':
            fillField(request.fieldSelector, request.value);
            break;
    }
}

function observeDOMChanges() {
    const observer = new MutationObserver((mutations) => {
        let shouldReanalyze = false;
        
        for (const mutation of mutations) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if added nodes contain form fields
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const formFields = node.querySelectorAll('input, select, textarea');
                        if (formFields.length > 0) {
                            shouldReanalyze = true;
                            break;
                        }
                    }
                }
            }
        }
        
        if (shouldReanalyze) {
            setTimeout(analyzePage, 500);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

async function analyzePage() {
    if (!settings.autoFillEnabled || !isAuthenticated) {
        return;
    }
    
    console.log('Analyzing page for form fields...');
    
    // Clear previous highlights and suggestions
    clearAllHighlights();
    
    // Extract form fields
    const fields = extractFormFields();
    
    if (fields.length === 0) {
        console.log('No form fields found');
        return;
    }
    
    console.log(`Found ${fields.length} form fields`);
    
    // Match fields to company data
    for (const field of fields) {
        await processField(field);
    }
}

function extractFormFields() {
    const fields = [];
    const formElements = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea');
    
    for (const element of formElements) {
        const field = {
            element: element,
            selector: generateSelector(element),
            tag: element.tagName.toLowerCase(),
            type: element.type || element.tagName.toLowerCase(),
            name: element.name || '',
            id: element.id || '',
            className: element.className,
            placeholder: element.placeholder || '',
            label: findLabel(element),
            value: element.value || '',
            isRequired: element.required || element.hasAttribute('required')
        };
        
        fields.push(field);
    }
    
    return fields;
}

function findLabel(element) {
    // Check for explicit label with 'for' attribute
    if (element.id) {
        const label = document.querySelector(`label[for="${element.id}"]`);
        if (label) {
            return label.textContent.trim();
        }
    }
    
    // Check for parent label
    let parent = element.parentElement;
    while (parent) {
        if (parent.tagName === 'LABEL') {
            return parent.textContent.trim();
        }
        parent = parent.parentElement;
    }
    
    // Check for preceding text
    let prev = element.previousSibling;
    while (prev) {
        if (prev.nodeType === Node.TEXT_NODE && prev.textContent.trim()) {
            return prev.textContent.trim();
        }
        if (prev.nodeType === Node.ELEMENT_NODE && prev.tagName === 'LABEL') {
            return prev.textContent.trim();
        }
        prev = prev.previousSibling;
    }
    
    // Fallback to placeholder or name
    return element.placeholder || element.name || '';
}

function generateSelector(element) {
    if (element.id) {
        return `#${element.id}`;
    }
    
    if (element.name) {
        return `[name="${element.name}"]`;
    }
    
    // Build a unique selector using CSS path
    let path = [];
    let current = element;
    
    while (current && current !== document.body) {
        let selector = current.tagName.toLowerCase();
        
        if (current.id) {
            selector += `#${current.id}`;
            path.unshift(selector);
            break;
        }
        
        if (current.className && typeof current.className === 'string') {
            const classes = current.className.split(' ').filter(c => c);
            if (classes.length) {
                selector += '.' + classes.join('.');
            }
        }
        
        const siblings = current.parentElement ? 
            Array.from(current.parentElement.children).filter(c => c.tagName === current.tagName) : [];
        if (siblings.length > 1) {
            const index = siblings.indexOf(current) + 1;
            selector += `:nth-of-type(${index})`;
        }
        
        path.unshift(selector);
        current = current.parentElement;
    }
    
    return path.join(' > ');
}

async function processField(field) {
    // Skip already filled fields
    if (field.value && field.value.trim() !== '') {
        return;
    }
    
    // Get field label
    const label = field.label || field.placeholder || field.name;
    if (!label) {
        return;
    }
    
    // Match field to data
    const match = await matchFieldToData(label, field.type);
    
    if (!match || match.confidence < settings.confidenceThreshold) {
        if (settings.showSuggestions && match && match.confidence > 0.3) {
            showSuggestion(field, match);
        }
        return;
    }
    
    // Get the actual value to fill
    const fillValue = await getFillValue(match);
    
    if (fillValue) {
        if (match.confidence >= 0.9) {
            // High confidence - auto-fill
            fillField(field, fillValue);
            highlightField(field, 'auto-filled', match.confidence);
        } else if (settings.showSuggestions) {
            // Medium confidence - show suggestion
            showSuggestion(field, match, fillValue);
        }
    }
}

async function matchFieldToData(label, fieldType) {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'matchField',
            label: label,
            fieldType: fieldType
        });
        
        return response.match;
    } catch (error) {
        console.error('Field matching error:', error);
        return null;
    }
}

async function getFillValue(match) {
    if (!match || !match.source || !match.field) {
        return null;
    }
    
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'getFillValue',
            source: match.source,
            field: match.field,
            confidence: match.confidence
        });
        
        return response.value;
    } catch (error) {
        console.error('Get fill value error:', error);
        return null;
    }
}

function fillField(field, value) {
    if (!field.element || !value) {
        return;
    }
    
    // Dispatch appropriate events based on field type
    const element = field.element;
    
    if (element.tagName === 'SELECT') {
        // For select dropdowns
        const option = Array.from(element.options).find(opt => 
            opt.text.toLowerCase() === String(value).toLowerCase() ||
            opt.value.toLowerCase() === String(value).toLowerCase()
        );
        if (option) {
            element.value = option.value;
            triggerEvent(element, 'change');
        }
    } else if (element.type === 'checkbox' || element.type === 'radio') {
        // For checkboxes and radio buttons
        const boolValue = value === true || value === 'true' || value === '1' || value === 'yes';
        if (element.checked !== boolValue) {
            element.checked = boolValue;
            triggerEvent(element, 'change');
        }
    } else {
        // For text inputs, textareas, etc.
        const originalValue = element.value;
        element.value = value;
        
        if (originalValue !== value) {
            triggerEvent(element, 'input');
            triggerEvent(element, 'change');
            triggerEvent(element, 'blur');
        }
    }
    
    // Track successful fill
    chrome.runtime.sendMessage({
        action: 'trackFormFill',
        data: {
            fieldType: field.type,
            fieldLabel: field.label,
            confidence: field.confidence,
            timestamp: new Date().toISOString(),
            url: window.location.href
        }
    });
}

function triggerEvent(element, eventType) {
    const event = new Event(eventType, { bubbles: true, cancelable: true });
    element.dispatchEvent(event);
    
    // Also trigger React/Vue events if needed
    const reactEvent = new Event(eventType, { bubbles: true });
    element.dispatchEvent(reactEvent);
}

function highlightField(field, status, confidence) {
    if (!settings.highlightFields) {
        return;
    }
    
    const element = field.element;
    const originalBorder = element.style.border;
    const originalBackground = element.style.backgroundColor;
    
    let color;
    if (status === 'auto-filled') {
        color = confidence >= 0.9 ? '#4CAF50' : '#FFC107';
    } else {
        color = '#2196F3';
    }
    
    element.style.border = `2px solid ${color}`;
    element.style.backgroundColor = `${color}20`;
    
    highlightedFields.push({
        element: element,
        originalBorder: originalBorder,
        originalBackground: originalBackground,
        timeout: setTimeout(() => {
            element.style.border = originalBorder;
            element.style.backgroundColor = originalBackground;
            const index = highlightedFields.findIndex(h => h.element === element);
            if (index !== -1) {
                highlightedFields.splice(index, 1);
            }
        }, 3000)
    });
}

function showSuggestion(field, match, value) {
    if (!settings.showSuggestions) {
        return;
    }
    
    const element = field.element;
    const rect = element.getBoundingClientRect();
    
    const suggestionBox = document.createElement('div');
    suggestionBox.className = 'tenderai-suggestion';
    suggestionBox.innerHTML = `
        <div class="tenderai-suggestion-content">
            <span class="tenderai-suggestion-label">Suggested: ${match.displayValue || value || 'N/A'}</span>
            <span class="tenderai-suggestion-confidence">${Math.round(match.confidence * 100)}% match</span>
            <button class="tenderai-apply-btn">Apply</button>
            <button class="tenderai-dismiss-btn">×</button>
        </div>
    `;
    
    suggestionBox.style.position = 'absolute';
    suggestionBox.style.top = `${rect.bottom + window.scrollY + 5}px`;
    suggestionBox.style.left = `${rect.left + window.scrollX}px`;
    suggestionBox.style.zIndex = '10000';
    
    // Add event listeners
    const applyBtn = suggestionBox.querySelector('.tenderai-apply-btn');
    const dismissBtn = suggestionBox.querySelector('.tenderai-dismiss-btn');
    
    applyBtn.addEventListener('click', () => {
        fillField(field, value || match.displayValue);
        suggestionBox.remove();
        highlightField(field, 'auto-filled', match.confidence);
    });
    
    dismissBtn.addEventListener('click', () => {
        suggestionBox.remove();
    });
    
    document.body.appendChild(suggestionBox);
    suggestionBoxes.push(suggestionBox);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (suggestionBox.parentElement) {
            suggestionBox.remove();
            const index = suggestionBoxes.indexOf(suggestionBox);
            if (index !== -1) {
                suggestionBoxes.splice(index, 1);
            }
        }
    }, 10000);
}

function clearAllHighlights() {
    // Clear field highlights
    for (const highlight of highlightedFields) {
        if (highlight.element) {
            highlight.element.style.border = highlight.originalBorder;
            highlight.element.style.backgroundColor = highlight.originalBackground;
        }
        if (highlight.timeout) {
            clearTimeout(highlight.timeout);
        }
    }
    highlightedFields = [];
    
    // Clear suggestion boxes
    for (const box of suggestionBoxes) {
        if (box.parentElement) {
            box.remove();
        }
    }
    suggestionBoxes = [];
}

// Inject styles
const styles = `
    .tenderai-suggestion {
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
        z-index: 10000;
        animation: tenderaiFadeIn 0.2s ease;
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
    }
    
    .tenderai-suggestion-confidence {
        background: #e3f2fd;
        color: #1976d2;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
    }
    
    .tenderai-apply-btn {
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 4px 12px;
        cursor: pointer;
        font-size: 12px;
        transition: background 0.2s;
    }
    
    .tenderai-apply-btn:hover {
        background: #45a049;
    }
    
    .tenderai-dismiss-btn {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        color: #999;
        padding: 0 4px;
    }
    
    .tenderai-dismiss-btn:hover {
        color: #666;
    }
    
    @keyframes tenderaiFadeIn {
        from {
            opacity: 0;
            transform: translateY(-5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;

const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);