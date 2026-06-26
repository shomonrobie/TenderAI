# modules/tutorial_page.py

import streamlit as st

def render_tutorial():
    """Full page tutorial for the main content area"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📚 Tutorial & Documentation</h1>
        <p>Learn how to use TenderAI features effectively</p>
    </div>
    """, unsafe_allow_html=True)
    
     # Create tabs - add BOQ tab
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🏗️ Rate Management",
        "🔐 RBAC",
        "📝 Manual Entry",
        "📊 Rate Viewer",
        "📋 Tender Management",
        "📄 BOQ Generator",
        "🎯 Bid Optimization",
        "🚀 Complete Workflow",
        "📦 Versions",
        "🔄 Rollback",
        "🔍 Debug Mode"
    ])
    
    with tab1:
        render_pwd_lged_tutorial()
    
    with tab2:
        render_rbac_tutorial()
    
    with tab3:
        render_manual_entry_tutorial()
    
    with tab4:
        render_viewer_tutorial()
    
    with tab5:
        render_boq_tutorial()  # NEW
    
    with tab6:
        render_version_tutorial()
    
    with tab7:
        render_rollback_tutorial()
    
    with tab8:
        render_debug_tutorial()


def render_pwd_lged_tutorial():
    """Tutorial for PWD and LGED rate management"""
    
    st.markdown("### 🏗️ PWD & LGED Rate Management")
    
    st.markdown("""
    The system supports two separate rate schedules:
    
    **PWD (Public Works Department)**
    - Used for building construction, government structures
    - Last updated: 2022
    - Zones: Dhaka, Chattogram, Khulna, Rajshahi
    
    **LGED (Local Government Engineering Department)**
    - Used for roads, bridges, culverts, rural infrastructure
    - Last updated: August 2025
    - Zones: Zone-A (Dhaka), Zone-B (Chattogram), Zone-C (Rajshahi), Zone-D (Khulna)
    
    **Key Concepts:**
    
    Parent Items - Items without rates that serve as descriptive headers
    Example: 1.01 - Erection and maintenance of site office
    
    Child Items - Items with actual rates that belong to a parent
    Example: 1.01.01 - Site office 10 sqm with rate 51,705.44
    
    Chapters - Groups of related items (e.g., Chapter 1: General Site Facilities)
    
    Versions - Different editions of rate schedules (2022, 2025, etc.)
    """)
    
    st.info("💡 Tip: Always create parent items before adding child items")


def render_rbac_tutorial():
    """Tutorial for Role-Based Access Control"""
    
    st.markdown("### 🔐 Role-Based Access Control (RBAC)")
    
    st.markdown("""
    The system uses roles to control what users can do. Each role has specific permissions:
    
    **Viewer**
    - Can only view rates
    - Cannot edit or delete anything
    
    **Data Entry**
    - Can view, add, and edit rates
    - Cannot delete items
    - Cannot manage users or roles
    
    **Analyst**
    - Can view and edit rates
    - Can run analysis on tender data
    - Cannot delete or manage users
    
    **Manager**
    - Can view, add, edit, and delete rates
    - Can manage tenders
    - Cannot manage system users
    
    **Company Admin**
    - Full control over company data
    - Can manage users within their company
    - Can manage versions
    - Cannot manage system-wide settings
    
    **System Admin**
    - Full system access
    - Can manage all users, roles, and data
    - Can access rollback and recovery features
    
    **Admin**
    - Highest level access
    - Can modify role permissions
    - Can access all system features
    
    **How Permissions Work:**
    
    When you try to edit a rate, the system checks your role. If your role has 'edit_rates' permission, you can make changes. If not, the edit buttons will be disabled or hidden.
    
    **Audit Log:**
    All actions (create, update, delete) are logged with:
    - Who made the change
    - When it was made
    - What was changed (old vs new values)
    - User's role at the time
    """)
    
    st.warning("⚠️ Only System Admin and Admin can modify role permissions")


def render_manual_entry_tutorial():
    """Tutorial for manual rate entry"""
    
    st.markdown("### 📝 Manual Rate Entry")
    
    st.markdown("""
    The manual entry system allows you to add rates without PDF parsing. It has four main sections:
    
    **1. Zones**
    - Define geographical zones
    - Set accessibility bonus percentages
    - PWD has 4 fixed zones, LGED zones can be customized
    
    **2. Chapters**
    - Create chapter numbers and names
    - Example: Chapter 1 - General, Site Facilities and Safety
    - Each rate item belongs to a chapter
    
    **3. Parents**
    - Create parent items (no rates)
    - Each parent must belong to a chapter
    - Parent codes use format: 1.01 or 01.1
    
    **4. Children**
    - Create child items with rates
    - Each child must have a parent
    - Child codes must start with parent code: 1.01.01
    - Enter rates for each zone
    
    **Editing Data:**
    - Double-click any cell in the data table to edit
    - Changes are saved when you click outside the cell
    - All changes are logged in the audit trail
    
    **Adding Multiple Items:**
    - Use the Add forms to add one item at a time
    - Use CSV upload for bulk import
    - Data can be exported to CSV at any time
    """)
    
    st.success("✅ Tip: Child codes should always start with their parent code for proper hierarchy")


def render_viewer_tutorial():
    """Tutorial for rate viewer and export"""
    
    st.markdown("### 📊 Rate Viewer & Export")
    
    st.markdown("""
    The Rate Viewer provides a comprehensive interface to browse rates:
    
    **Features:**
    
    **Filtering**
    - Filter by Chapter: Show only items from specific chapters
    - Filter by Zone: View rates for specific zones
    - Search: Find items by code or description
    
    **Pagination**
    - Choose how many items per page (10, 25, 50, 100, 200)
    - Navigate between pages with Previous/Next buttons
    
    **Data Display**
    - Items are pivoted to show zones as columns
    - Rates are formatted with currency symbols
    - Click column headers to sort
    
    **Export Options**
    - Download current view as CSV
    - Export all data (respects current filters)
    
    **Summary Statistics**
    - View min, max, average rates by zone
    - See count of items per zone
    
    **Tips:**
    - Use filters first to narrow down data before exporting
    - Check the summary statistics to understand rate ranges
    - Search is case-insensitive and matches partial text
    """)
    
    st.info("💡 The viewer shows data from the active version only")


def render_version_tutorial():
    """Tutorial for version management"""
    
    st.markdown("### 📦 Version Management")
    
    st.markdown("""
    Version management allows you to track different editions of rate schedules:
    
    **Why Versions?**
    - PWD rates are updated every 3-5 years
    - LGED rates were updated in August 2025
    - Old rates need to be kept for reference
    - Different projects may use different rate editions
    
    **Version Features:**
    
    **Create Version**
    - Name the version (e.g., "LGED Schedule 2025")
    - Set edition year and effective date
    - Option to set as active immediately
    
    **Active Version**
    - Only one version can be active at a time
    - The rate viewer shows data from the active version
    - Child items are linked to specific versions
    
    **Version History**
    - View all versions with their details
    - See who created each version
    - Track when versions were activated
    
    **Switching Versions**
    - Select any version and click "Set as Active"
    - Previous active version becomes archived
    - All data remains available for reference
    
    **Best Practices:**
    - Always create a new version when rates change
    - Never delete old versions (keep for audit)
    - Document version changes in notes
    """)
    
    st.warning("⚠️ Changing active version affects what rates appear in the viewer")


def render_rollback_tutorial():
    """Tutorial for rollback and recovery"""
    
    st.markdown("### 🔄 Rollback & Recovery")
    
    st.markdown("""
    The rollback system protects your data and allows recovery from mistakes:
    
    **Snapshots**
    - Point-in-time backups of your rate data
    - Can be created manually or automatically
    - Capture parents, children, and all rates
    
    **When Snapshots Are Created**
    - Automatically before major imports
    - Automatically before rollback operations
    - Manually before making batch changes
    - Manually before version switches
    
    **Rolling Back**
    - Select any snapshot from the list
    - Click "Rollback to this snapshot"
    - System creates an auto-backup first
    - All data is restored to snapshot state
    
    **Import History**
    - Tracks all data imports
    - Shows who imported, when, and how many items
    - Helps identify when issues were introduced
    
    **Best Practices:**
    - Create a snapshot before making bulk changes
    - Create a snapshot before importing new data
    - Keep snapshots for major milestones
    - Delete old snapshots to save space
    
    **Recovery Process:**
    1. Identify when the issue occurred
    2. Find a snapshot from before that time
    3. Rollback to restore data
    4. Verify data is correct
    """)
    
    st.info("💡 Snapshots store only data, not file attachments or user settings")



def render_boq_tutorial():
    """Tutorial for BOQ Generator"""
    
    st.markdown("### 📄 BOQ Generator")
    
    st.markdown("""
    The BOQ Generator automatically matches your e-GP BOQ items with PWD/LGED rate schedules.
    
    **How It Works:**
    
    1. **Upload BOQ File** - Upload your e-GP BOQ Excel template
    2. **Select Rate Source** - Choose PWD or LGED rate schedule
    3. **Select Zone** - Choose your project's geographical zone
    4. **Automatic Matching** - System matches items by:
    - Exact item code match
    - Exact description match
    - Partial description match (common keywords)
    - Number pattern match
    5. **Review Results** - See matched vs unmatched items
    6. **Download BOQ** - Get Excel with rates filled in
    
    **Required Excel Columns:**
    - `Item Code (if any)` - Item code from schedule
    - `Description of Item` - Item description
    - `Quantity` - Quantity of the item
    
    **Subscription Limits:**
    - Free Plan: 5 BOQ generations per month
    - Basic Plan: 20 BOQ generations per month
    - Professional Plan: 50 BOQ generations per month
    - Enterprise Plan: Unlimited BOQ generations
    
    **Output Files:**
    The generated BOQ Excel contains three sheets:
    - **Matched Items** - Items with automatically filled rates
    - **Unmatched Items** - Items requiring manual rate entry
    - **Summary** - Generation statistics and total cost
    
    **Tips for Better Matching:**
    - Use exact item codes when available
    - Ensure descriptions match PWD/LGED wording
    - Check unmatched items and manually enter rates
    - Verify rates before finalizing bids
    
    **BOQ History:**
    - Tracks all your BOQ generations
    - Shows file names, item counts, and timestamps
    - Admins can see all users' history
    """)
    
    st.info("💡 BOQ generations count towards your monthly subscription limit")


def render_debug_tutorial():
    """Tutorial for debug mode"""
    
    st.markdown("### 🔍 Debug Mode")
    
    st.markdown("""
    Debug mode helps troubleshoot issues with data import and display.
    
    **Enabling Debug Mode**
    - Check the "Show Debug Info" checkbox
    - Available in Rate CRUD forms and Rate Viewer
    - Does not affect performance for normal users
    
    **What Debug Mode Shows**
    
    **Data Types**
    - Shows what type of data is in each column
    - Helps identify conversion issues
    
    **Sample Data**
    - Displays first few rows of loaded data
    - Shows actual values from database
    
    **Database Operations**
    - Confirms when data is inserted or updated
    - Shows SQL errors if they occur
    
    **BOQ Matching Debug**
    - Shows matching logic used for each item
    - Displays match confidence scores
    - Helps improve matching accuracy
    
    **Common Debug Scenarios**
    
    *Rates not showing in viewer*
    - Check debug to see if data loaded
    - Verify unit_rate is numeric
    - Check zone names match
    
    *BOQ items not matching*
    - Check item codes and descriptions
    - Verify rate data exists for selected zone
    - Review partial match criteria
    
    **When to Use Debug Mode**
    - When data doesn't appear as expected
    - When BOQ matching fails
    - When imports fail
    - When reporting issues to support
    """)
    
    st.success("✅ Turn off debug mode for normal use to keep the interface clean")
def render_bid_optimization_tutorial():
    """Tutorial for Bid Optimization workflow"""
    
    st.markdown("### 🎯 Bid Optimization Workflow")
    
    st.markdown("""
    The Bid Optimization system helps you determine the optimal bid amount using AI and PPR 2025 guidelines.
    
    **Complete Workflow:**
    Create Tender → 2. Generate BOQ → 3. Add Competitors → 4. Run Optimization → 5. Submit Bid

        **Step 1: Create Tender**
    - Go to Tender Management tab
    - Click "Create New Tender"
    - Enter tender details (ID, title, estimate, deadline)
    - Or upload PDF to auto-fill form

    **Step 2: Generate BOQ**
    - Go to BOQ Generator tab
    - Select your tender
    - Upload BOQ Excel file
    - System matches rates from PWD/LGED database
    - Download BOQ with filled rates

    **Step 3: Add Competitor Intelligence**
    - Go to BOQ to Bid Optimizer tab
    - Select your tender
    - Add competitor bids you know
    - System tracks competitor patterns

    **Step 4: Run Optimization**
    - Configure risk tolerance (Aggressive/Moderate/Conservative)
    - Set NPPI factor (default 0.920)
    - Click "Run Bid Optimization"
    - View three-tier analysis results

    **Step 5: Review Results**

    **Basic Analysis**
    - Simple average-based calculation
    - Fast estimation without complex data
    - Good for quick reference

    **Advanced Analysis (PPR 2025)**
    - Uses NPPI (Non-Participatory Price Index)
    - SLT (Substantially Low Tender) threshold calculation
    - Weighted average of competitor bids, estimate, and NPPI
    - Compliant with Bangladesh PPR 2025 rules

    **Enhanced Analysis (ML)**
    - Machine learning predictions
    - Seasonality and market factors
    - Competitor behavior patterns
    - Highest accuracy

    **Step 6: Take Action**
    - Apply recommended bid to tender
    - Generate professional HTML/PDF report
    - Submit bid directly from optimizer

    **Understanding Key Metrics:**

    | Metric | Description |
    |--------|-------------|
    | NPPI Factor | Non-Participatory Price Index (market average) |
    | SLT Threshold | Price below which bid may be rejected |
    | Win Probability | Statistical chance of winning |
    | Bid Ratio | Your bid as % of official estimate |
    | Risk Level | LOW/MEDIUM/HIGH based on bid aggressiveness |

    **Best Practices:**
    - Always generate BOQ before optimization
    - Add as many competitor bids as possible
    - Use Moderate risk for first-time bidders
    - Review SLT threshold - bids below may be rejected
    - Generate report for management approval
    """)

    st.info("💡 The optimization uses PPR 2025 compliant methodology")

    st.warning("⚠️ Bids below SLT threshold may be rejected automatically")


def render_complete_workflow_tutorial():
    """Complete end-to-end workflow tutorial"""

    st.markdown("### 🚀 Complete Tender to Bid Workflow")

    st.markdown("""
    This guide shows how to use TenderAI from start to finish.

    **📋 Phase 1: Tender Setup**

    1. **Create Tender Record**
    - Navigate to Tender Management
    - Fill tender details (ID, estimate, deadline)
    - Or upload tender notice PDF for auto-fill

    2. **Set Up Team (Optional)**
    - Assign Bid Manager, Technical Lead
    - Add team members with roles
    - Track responsibilities

    **📄 Phase 2: BOQ Generation**

    3. **Upload BOQ Template**
    - Go to BOQ Generator
    - Select your tender
    - Upload Excel with items, descriptions, quantities

    4. **Rate Matching**
    - System matches items with PWD/LGED database
    - Exact code match first
    - Description match second
    - Partial match third

    5. **Download BOQ**
    - Get Excel with rates filled
    - Review matched and unmatched items
    - Manually enter missing rates if needed

    **🎯 Phase 3: Bid Optimization**

    6. **Add Competitor Intelligence**
    - Go to BOQ to Bid Optimizer
    - Enter known competitor bids
    - System learns competitor patterns

    7. **Configure Optimization**
    - Select procurement type (works/goods/services)
    - Choose risk tolerance
    - Set NPPI factor (or use default)

    8. **Run Analysis**
    - Click "Run Bid Optimization"
    - View three-tier comparison
    - Review SLT threshold compliance

    **📊 Phase 4: Decision & Submission**

    9. **Review Results**
    - Check recommended bid amount
    - Verify win probability
    - Assess risk level

    10. **Generate Report**
        - Create professional HTML report
        - Download PDF for management
        - Share with team

    11. **Apply & Submit**
        - Click "Apply to Tender"
        - Final review in Tender Management
        - Submit bid before deadline

    **🎉 Success!**

    Your bid is now submitted with AI-optimized pricing.

    **Pro Tips:**
    - Update competitor bids as you learn more
    - Use Historical Data tab to track win/loss patterns
    - Review past performance to refine risk tolerance
    - Keep PWD/LGED rates updated for accurate BOQ
    """)

    st.success("✅ Following this workflow maximizes win probability while maintaining profitability")

def render_tender_management_tutorial():
    """Tutorial for Tender Management"""
    
    st.markdown("### 📋 Tender Management")
    
    st.markdown("""
    **Creating a Tender:**
    
    1. Go to Tender Management tab
    2. Click "Create New Tender"
    3. Fill required fields:
       - Tender ID (unique identifier)
       - Tender Title
       - Procuring Entity
       - Official Estimate
       - Submission Deadline
    
    **PDF Upload:**
    - Upload tender notice PDF
    - System auto-extracts fields
    - Review and confirm extracted data
    - Edit manually if needed
    
    **Tracking Bids:**
    - Update your bid amount
    - Submit final bid
    - Record result (Won/Lost)
    - Track rank and winning amount
    
    **Team Management:**
    - Assign Bid Manager
    - Assign Technical Lead
    - Add team members
    - Track responsibilities
    
    **Milestones:**
    - Create task deadlines
    - Assign to team members
    - Track completion status
    """)
