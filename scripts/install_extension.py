# scripts/install_extension.py
"""
Script to install/update the Chrome extension
"""

import os
import json
import shutil
import zipfile
from pathlib import Path

def create_extension_package():
    """Create a distributable Chrome extension package"""
    
    extension_dir = Path("extension")
    
    # Ensure extension directory exists
    extension_dir.mkdir(exist_ok=True)
    
    # Create icons directory
    icons_dir = extension_dir / "icons"
    icons_dir.mkdir(exist_ok=True)
    
    # Create placeholder icons (you should replace with actual icons)
    for size in [16, 32, 48, 128]:
        icon_path = icons_dir / f"icon{size}.png"
        if not icon_path.exists():
            print(f"⚠️ Placeholder: Create icon{size}.png in {icon_path}")
    
    # Create manifest.json
    manifest = {
        "manifest_version": 3,
        "name": "TenderAI Auto-Fill Assistant",
        "version": "1.0.0",
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
            "http://localhost:8501/*",
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
                "resources": ["icons/*", "styles.css"],
                "matches": ["<all_urls>"]
            }
        ]
    }
    
    with open(extension_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    print("✅ Created manifest.json")
    
    # Create zip file for distribution
    zip_path = Path("tenderai_extension.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in extension_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(extension_dir.parent)
                zipf.write(file_path, arcname)
    
    print(f"✅ Created extension package: {zip_path}")
    print("\nTo install the extension:")
    print("1. Open Chrome and go to chrome://extensions/")
    print("2. Enable 'Developer mode'")
    print("3. Click 'Load unpacked'")
    print(f"4. Select the '{extension_dir}' folder")
    print("\nOr distribute the zip file to users who can install via Developer mode")

def generate_extension_setup_instructions():
    """Generate setup instructions for users"""
    
    instructions = """
# TenderAI Chrome Extension Setup

## Installation

### Method 1: Developer Mode (Recommended for testing)
1. Download the `tenderai_extension.zip` file
2. Extract the zip file to a folder
3. Open Chrome and go to `chrome://extensions/`
4. Enable "Developer mode" (toggle in top right)
5. Click "Load unpacked"
6. Select the extracted extension folder
7. The extension icon should appear in your toolbar

### Method 2: Enterprise Deployment
For organization-wide deployment, use Chrome Enterprise policies:
- Add the extension ID to the force-installed list
- Configure policy to allow the extension on tender sites

## Configuration

1. Click the extension icon in the toolbar
2. Sign in with your TenderAI credentials
3. The extension will automatically detect tender forms
4. Auto-fill confidence threshold can be adjusted in settings

## Supported Sites
- e-GP Bangladesh (eptenders.gov.bd)
- e-Procurement (eprocure.gov.bd)
- DPP (dpp.gov.bd)
- Any tender portal with form fields

## Troubleshooting
- If forms aren't detected, refresh the page
- Check that you're logged into TenderAI
- Verify your subscription has auto-fill credits remaining
"""
    
    with open("EXTENSION_SETUP.md", "w") as f:
        f.write(instructions)
    print("✅ Created EXTENSION_SETUP.md")

if __name__ == "__main__":
    create_extension_package()
    generate_extension_setup_instructions()