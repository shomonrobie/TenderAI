@echo off
echo Creating ITMS project structure...

:: Root folder

:: Main files
type nul > itms\app.py
type nul > itms\requirements.txt

:: Database folder
mkdir itms\database
type nul > itms\database\db_manager.py

:: Modules folder
mkdir itms\modules
type nul > itms\modules\__init__.py
type nul > itms\modules\auth.py
type nul > itms\modules\admin.py
type nul > itms\modules\user_management.py
type nul > itms\modules\subscription.py
type nul > itms\modules\bid_optimizer.py
type nul > itms\modules\premium_features.py
type nul > itms\modules\advanced_bid_optimizer.py

:: Pages folder
mkdir itms\pages
type nul > itms\pages\__init__.py
type nul > itms\pages\home.py
type nul > itms\pages\about.py
type nul > itms\pages\contact.py
type nul > itms\pages\pricing.py
type nul > itms\pages\login.py
type nul > itms\pages\register.py
type nul > itms\pages\dashboard.py
type nul > itms\pages\admin_dashboard.py
type nul > itms\pages\user_management_page.py
type nul > itms\pages\subscription_page.py
type nul > itms\pages\profile.py
type nul > itms\pages\tender_analysis.py

:: Utils folder
mkdir itms\utils
type nul > itms\utils\helpers.py

:: Data folder
mkdir itms\data
type nul > itms\data\tender_system.db

echo.
echo ITMS project structure created successfully!
pause