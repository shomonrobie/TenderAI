# modules/tutorial.py

import streamlit as st
def render_tutorial():
    """Full page tutorial organized by user journey"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📚 TenderAI Learning Center</h1>
        <p>Your complete guide to winning more tenders with AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Welcome section
    st.info("""
    🎯 **Welcome to TenderAI!** This tutorial will guide you through the complete bidding process.
    Choose a topic below based on what you want to learn.
    """)
    
    # Main workflow visualization
    st.markdown("### 🚀 The Complete Bidding Workflow")
    
    workflow_cols = st.columns(5)
    workflow_steps = [
        ("1️⃣", "Create Tender", "📋"),
        ("2️⃣", "Generate BOQ", "📄"),
        ("3️⃣", "Add Competitors", "👥"),
        ("4️⃣", "Optimize Bid", "🎯"),
        ("5️⃣", "Submit & Win", "🏆")
    ]
    
    for i, (num, label, icon) in enumerate(workflow_steps):
        with workflow_cols[i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; background: #f0f4f8; border-radius: 10px;">
                <div style="font-size: 2rem;">{icon}</div>
                <div style="font-weight: bold;">{label}</div>
                <div style="font-size: 0.8rem; color: #666;">{num}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Create tabs organized by user journey
    tab_intro, tab_tender, tab_boq, tab_optimize, tab_rates, tab_admin, tab_advanced, tab_company_data, tab_extension = st.tabs([
        "🌟 Getting Started",
        "📋 Tender Management",
        "📄 BOQ Generation",
        "🎯 Bid Optimization",
        "🏗️ Rate Management",
        "👑 Admin Guide",
        "⚙️ Advanced Features",
        "🏢 Company Data",
        "📄 Extension"
    ])
    
    with tab_intro:
        render_getting_started()
    
    with tab_tender:
        render_tender_management_tutorial()
    
    with tab_boq:
        render_boq_tutorial()
    
    with tab_optimize:
        render_bid_optimization_tutorial()
    
    with tab_rates:
        render_rate_management_tutorial()
    
    with tab_admin:
        render_admin_tutorial()
    
    with tab_advanced:
        render_advanced_tutorial()
    
    with tab_company_data:
        render_company_data_management()
    
    with tab_extension:
        generate_extension_setup_instructions()


def render_getting_started():
    """Getting started guide for new users"""
    
    st.markdown("### 🌟 Welcome to TenderAI")
    
    st.markdown("""
    TenderAI helps you prepare competitive bids using AI-powered analysis and official PWD/LGED rate schedules.
    
    **What you can do with TenderAI:**
    
    | Feature | What it does | Who it's for |
    |---------|--------------|--------------|
    | 📋 Tender Management | Track all your tenders in one place | Everyone |
    | 📄 BOQ Generator | Auto-fill rates from official schedules | Estimators |
    | 🎯 Bid Optimizer | AI recommends optimal bid amount | Decision makers |
    | 🏗️ Rate Management | Import PWD/LGED rate schedules | Admins |
    | 📊 Reports | Professional bid analysis reports | Management |
    
    **Quick Start Guide:**
    
    1. **First Time Users**
       - Go to Rate Management → Import PWD/LGED rates
       - This is required for BOQ generation
    
    2. **Create Your First Tender**
       - Go to Tender Management → Create New Tender
       - Fill in tender details
    
    3. **Generate BOQ**
       - Go to BOQ Generator → Select tender
       - Upload your BOQ Excel file
    
    4. **Optimize Your Bid**
       - Go to BOQ to Bid Optimizer
       - Add competitor bids (if known)
       - Run AI analysis
    
    5. **Submit & Track**
       - Apply recommended bid
       - Track results in Tender Management
    """)
    
    # Role-based guide
    st.markdown("### 👥 Guide by Role")
    
    role_col1, role_col2, role_col3 = st.columns(3)
    
    with role_col1:
        st.markdown("""
        **📋 Estimator**
        - Create/manage tenders
        - Generate BOQs
        - Match rates from database
        - Export BOQ Excel files
        """)
    
    with role_col2:
        st.markdown("""
        **🎯 Decision Maker**
        - Review BOQ estimates
        - Add competitor intelligence
        - Run bid optimization
        - Review AI recommendations
        """)
    
    with role_col3:
        st.markdown("""
        **👑 Administrator**
        - Import rate schedules
        - Manage user roles
        - Configure system settings
        - View audit logs
        """)
    
    st.success("💡 **Pro Tip:** Start with the 'Complete Workflow' to see how all features work together!")


def render_tender_management_tutorial():
    """Tutorial for Tender Management"""
    
    st.markdown("### 📋 Tender Management")
    st.caption("Track all your tenders, manage bids, and monitor deadlines")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### ✨ Features
        
        **Create Tender**
        - Manual entry or PDF upload
        - Auto-extract from tender notice
        - All e-GP fields supported
        
        **Track Bids**
        - Set your bid amount
        - Update as needed
        - Submit final bid
        - Record results
        
        **Team Management**
        - Assign Bid Manager
        - Assign Technical Lead
        - Add team members
        - Track responsibilities
        """)
    
    with col2:
        st.markdown("""
        #### 📝 Step-by-Step
        
        **1. Create Tender**
        Tender Management → Create New Tender
        Fill: ID, Title, Entity, Estimate, Deadline
        
        **2. Set Your Bid**
        Active Tenders → Enter Bid Amount → Save

        **3. Submit Bid**
        Active Tenders → Submit → Confirm

        **4. Record Results**
        Won/Lost → Enter winning amount → Save
        """)
    st.info("💡 **Tip:** Use PDF upload to auto-fill tender details from notice documents")


def render_boq_tutorial():
    """Tutorial for BOQ Generator"""

    st.markdown("### 📄 BOQ Generator")
    st.caption("Automatically match BOQ items with official rate schedules")

    st.markdown("""
    #### How BOQ Generation Works
        Upload Excel → Match Rates → Review Results → Download BOQ

    **Step 1: Prepare Your BOQ File**

    Your Excel file must have these columns:
    - `Item Code (if any)` - Optional, helps with matching
    - `Description of Item` - Required for matching
    - `Quantity` - Required for calculation

    **Step 2: Select Rate Source**

    | Source | Best For |
    |--------|----------|
    | PWD | Building construction, government structures |
    | LGED | Roads, bridges, rural infrastructure |

    **Step 3: Choose Zone**

    | PWD Zones | LGED Zones |
    |-----------|------------|
    | Dhaka | Zone-A (Dhaka) |
    | Chattogram | Zone-B (Chattogram) |
    | Khulna | Zone-D (Khulna) |
    | Rajshahi | Zone-C (Rajshahi) |

    **Step 4: Matching Logic**

    The system matches items in this order:
    1. Exact code match
    2. Exact description match
    3. Partial description match (keywords)
    4. Number pattern match

    **Step 5: Review & Download**

    - Matched items have rates auto-filled
    - Unmatched items need manual entry
    - Download Excel with rates and word conversions
    """)

    st.warning("⚠️ **Note:** Unmatched items require manual rate entry. Enable Debug Mode to see why items didn't match.")


def render_bid_optimization_tutorial():
    """Tutorial for Bid Optimization"""

    st.markdown("### 🎯 Bid Optimization")
    st.caption("AI-powered bid recommendation using PPR 2025 methodology")

    st.markdown("""
    #### The Three-Tier Analysis

    TenderAI provides three levels of analysis to help you make informed decisions:

    | Tier | Method | Best For | Accuracy |
    |------|--------|----------|----------|
    | **Basic** | Simple average of competitors | Quick estimates | Low |
    | **Advanced** | PPR 2025 compliant (NPPI + SLT) | Official bids | High |
    | **Enhanced** | Machine learning + market factors | Competitive bids | Very High |

    #### Key Concepts

    **NPPI (Non-Participatory Price Index)**
    - Market average price index
    - Default: 0.920 (92% of estimate)
    - Can use company-specific historical NPPI

    **SLT (Substantially Low Tender) Threshold**
    - Bids below this may be rejected
    - Calculated as: Weighted Average - Standard Deviation
    - Stay above SLT to avoid rejection

    **Weighted Average Formula (PPR 2025)**
    Weighted Avg = (0.5 × Competitor Avg) + (0.2 × Estimate) + (0.3 × NPPI Price)

    #### Risk Tolerance Guide

    | Setting | Strategy | Win Probability | Profit Margin |
    |----------|----------|-----------------|---------------|
    | Aggressive | Low bid, high risk | High | Low |
    | Moderate | Balanced approach | Medium | Medium |
    | Conservative | High bid, low risk | Low | High |

    #### How to Use

    1. **Prepare Data**
    - Generate BOQ first (or use official estimate)
    - Add known competitor bids

    2. **Configure**
    - Select procurement type
    - Choose risk tolerance
    - Set NPPI factor (optional)

    3. **Run Analysis**
    - Click "Run Bid Optimization"
    - Review three-tier comparison

    4. **Take Action**
    - Apply recommended bid to tender
    - Generate professional report
    - Submit bid
    """)

    st.success("✅ **Best Practice:** Use Advanced analysis for PPR compliance. Use Enhanced for competitive markets.")


def render_rate_management_tutorial():
    """Combined tutorial for rate management"""

    st.markdown("### 🏗️ Rate Management")
    st.caption("Import and manage PWD/LGED rate schedules")

    tab_pwd, tab_lged, tab_manual = st.tabs([
        "🏗️ PWD Rates",
        "🛣️ LGED Rates",
        "📝 Manual Entry"
    ])

    with tab_pwd:
        st.markdown("""
        #### PWD Rate Schedule
        
        **About PWD Rates**
        - Used for building construction
        - Last updated: 2022
        - 4 zones: Dhaka, Chattogram, Khulna, Rajshahi
        
        **Import Methods**
        
        | Method | Best For | Speed |
        |--------|----------|-------|
        | Quick Test | Validation | Fast (10 pages) |
        | Batch Import | Large files | Moderate |
        | Full Import | Complete schedule | Slow |
        
        **Import Steps:**
        1. Go to PWD Management → Import Schedule
        2. Upload PWD PDF
        3. Choose import method
        4. Review extracted data
        5. Save to database
        """)

    with tab_lged:
        st.markdown("""
        #### LGED Rate Schedule
        
        **About LGED Rates**
        - Used for roads, bridges, rural infrastructure
        - Last updated: August 2025
        - Zones: A (Dhaka), B (Chattogram), C (Rajshahi), D (Khulna)
        - 5% accessibility bonus for remote areas
        
        **Zone Details**
        
        | Zone | Divisions | Bonus |
        |------|-----------|-------|
        | A | Dhaka, Mymensingh | 0% |
        | B | Chattogram, Sylhet | 0% |
        | C | Rajshahi, Rangpur | 0% |
        | D | Khulna, Barishal | 5% |
        
        **Import Steps:**
        1. Go to LGED Management → Import Schedule
        2. Upload LGED PDF (August 2025)
        3. Select import method
        4. Review extracted data
        5. Save to database
        """)

    with tab_manual:
        st.markdown("""
        #### Manual Rate Entry
        
        **When to Use Manual Entry**
        - PDF parsing fails
        - Adding missing rates
        - Correcting extracted data
        - Custom rates
        
        **Entity Hierarchy**
        Chapter (e.g., 01 - General)
    └── Parent (e.g., 1.01 - Site Office) [NO rates]
    └── Child (e.g., 1.01.01 - 10 sqm office) [HAS rates]

    **Entry Order**
    1. Create Chapters first
    2. Create Parents (no rates)
    3. Create Children (with rates)

    **Editable Table**
    - Double-click any cell to edit
    - Changes auto-save to session
    - Click "Save to Database" to commit
    """)

    st.info("💡 **Tip:** Import rates before generating BOQ for best matching results")


def render_admin_tutorial():
    """Admin guide"""

    st.markdown("### 👑 Administrator Guide")

    st.markdown("""
    #### User Management

    **Role Permissions**

    | Role | Create | Read | Update | Delete | Manage Users |
    |------|--------|------|--------|--------|--------------|
    | Viewer | ❌ | ✅ | ❌ | ❌ | ❌ |
    | Data Entry | ✅ | ✅ | ✅ | ❌ | ❌ |
    | Analyst | ❌ | ✅ | ✅ | ❌ | ❌ |
    | Manager | ✅ | ✅ | ✅ | ❌ | ❌ |
    | Company Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
    | System Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

    #### Subscription Management

    **Plan Limits**

    | Plan | BOQ/Month | Analyses/Month | Users |
    |------|-----------|----------------|-------|
    | Free | 5 | 5 | 1 |
    | Basic | 20 | 30 | 3 |
    | Professional | 50 | Unlimited | 10 |
    | Enterprise | Unlimited | Unlimited | Unlimited |

    #### System Configuration

    **Required Setup**
    1. Import PWD/LGED rate schedules
    2. Configure user roles and permissions
    3. Set subscription plans
    4. Review audit logs

    **Maintenance Tasks**
    - Monthly: Check rate updates
    - Quarterly: Review user activity
    - Yearly: Archive old data
    """)

    st.warning("⚠️ Only System Admin can modify role permissions and system settings")


def render_advanced_tutorial():
    """Advanced features tutorial"""

    st.markdown("### ⚙️ Advanced Features")

    tab_versions, tab_rollback, tab_debug = st.tabs([
    "📦 Version Management",
    "🔄 Rollback & Recovery",
    "🔍 Debug Mode"
    ])

    with tab_versions:
        st.markdown("""
        #### Version Management

        **Why Versions Matter**
        - Rate schedules update every 3-5 years
        - Keep historical rates for reference
        - Different projects use different editions

        **Managing Versions**

        1. **Create Version**
        - After importing new rates
        - Name and year required
        - Option to set as active

        2. **Active Version**
        - Only one active at a time
        - BOQ Generator uses active version
        - Viewer shows active version

        3. **Switching Versions**
        - Select version → Activate
        - Previous becomes archived
        - Data remains accessible
        """)

    with tab_rollback:
        st.markdown("""
        #### Rollback & Recovery

        **Snapshots**
        - Point-in-time backups
        - Created automatically before imports
        - Can be created manually

        **When to Rollback**
        - Import error
        - Wrong rates applied
        - Accidental deletion
        - Data corruption

        **How to Rollback**
        1. Go to Rollback Management
        2. Select snapshot
        3. Click "Rollback"
        4. System creates auto-backup first
        5. Data restored to snapshot state

        **Best Practices**
        - Create snapshot before bulk changes
        - Keep snapshots for major milestones
        - Delete old snapshots to save space
        """)

        with tab_debug:
            st.markdown("""
            #### Debug Mode

            **Enabling Debug**
            - Check "Show Debug Info" checkbox
            - Available in Rate CRUD and Viewer
            - No performance impact for normal users

            **What Debug Shows**

            | Information | Purpose |
            |-------------|---------|
            | Data types | Identify conversion issues |
            | Sample data | Verify correct values |
            | Database ops | Confirm saves/updates |
            | Matching logic | See why items match/fail |

            **Common Debug Scenarios**

            *No rates found in BOQ*
            - Debug shows available editions
            - Check zone and year match
            - Verify rates imported

            *Edits not saving*
            - Debug shows SQL errors
            - Check user permissions
            - Verify database connection

            **When to Use**
            - Troubleshooting issues
            - Reporting bugs
            - Validating imports
            """)

            st.success("✅ Enable Debug Mode when reporting issues to support")


    # Also keep the sidebar tutorial for quick reference
def render_sidebar_tutorial():
    """Compact tutorial for sidebar"""

    with st.expander("📚 Quick Help", expanded=False):
        st.markdown("""
        **Need help?**

        **Workflow:**
        1. Create Tender (Tender Management)
        2. Generate BOQ (BOQ Generator)
        3. Optimize Bid (BOQ to Bid Optimizer)
        4. Submit Bid (Tender Management)

        **Common Tasks:**
        - 📄 Import rates: Admin Dashboard → Rate Management
        - 👥 Add team: Tender Management → Team
        - 📊 View history: Analysis History
        - 🔄 Rollback: Rollback Management

        **Support:**
        - 📚 Full tutorial: Click Tutorial button above
        - 🐛 Enable Debug: Check "Show Debug Info"
        - 📧 Contact: support@tenderai.com
        """)

        if st.button("📖 Open Full Tutorial", use_container_width=True):
            st.session_state.page = "tutorial"
            st.rerun()


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
    
#     with open("EXTENSION_SETUP.md", "w") as f:
#         f.write(instructions)
#     print("✅ Created EXTENSION_SETUP.md")

# if __name__ == "__main__":
#     create_extension_package()
#     generate_extension_setup_instructions()
    
        
def render_company_data_management():
    """
    Full Company Data Management tutorial including Custom Field Mappings
    This is the comprehensive tutorial for end users
    """
    st.markdown("""
    ## 🏢 Company Data Management

    Your company data is the foundation of successful bidding. 
    This guide shows you how to manage it effectively.
    """)

    # Overview
    st.info("""
    💡 **Key Concept:** The more complete your company data, the better TenderAI can help you.
    All data entered here can be auto-filled into tender forms with one click!
    """)

    # Table of contents
    st.markdown("### 📚 In This Guide")
    toc_cols = st.columns(4)
    with toc_cols[0]:
        st.markdown("""
        - [Basic Info](#basic-info)
        - [Licenses](#licenses)
        - [Financial Data](#financial-data)
        """)
    with toc_cols[1]:
        st.markdown("""
        - [Key Personnel](#personnel)
        - [Equipment](#equipment)
        - [Experience](#experience)
        """)
    with toc_cols[2]:
        st.markdown("""
        - [Documents](#documents)
        - [Field Mappings](#field-mappings)
        - [Auto-Fill](#auto-fill)
        """)
    with toc_cols[3]:
        st.markdown("""
        - [Best Practices](#best-practices)
        - [FAQs](#faqs)
        - [Support](#support)
        """)

    st.markdown("---")

    # ========================================================================
    # SECTION 1: BASIC INFO
    # ========================================================================
    st.markdown('<a name="basic-info"></a>', unsafe_allow_html=True)
    st.markdown("### 🏢 Basic Information")
    st.markdown("""
    This is your company's core identity. Keep this information accurate and up-to-date.

    **Fields to Fill:**
    - **Company Name** - Your registered business name
    - **Email & Phone** - Primary contact information
    - **Registration & VAT Numbers** - Official identifiers
    - **Address** - Your registered office address
    - **Division & District** - Your business location

    **Pro Tip:** These fields auto-fill into tender forms when you use the Chrome extension!

    **Visual Indicator:** Look for the 🔗 icon - it means the field is mapped for auto-fill.
    """)

    # Show a sample of auto-fill mapping
    with st.expander("🔗 See Auto-Fill in Action", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **📋 Tender Form Field**
            Company Name: []
            TIN Number: []
            Address: [__________________]

            text
            """)
        with col2:
            st.markdown("""
            **📊 Your Data**
            Company Name: ABC Construction Ltd 🔗
            TIN Number: 1234567890 🔗
            Address: 123, Dhaka, Bangladesh 🔗

            text
            """)
    st.success("✅ Fields with 🔗 are automatically filled from your company data!")

    st.markdown("---")

    # ========================================================================
    # SECTION 2: LICENSES
    # ========================================================================
    st.markdown('<a name="licenses"></a>', unsafe_allow_html=True)
    st.markdown("### 📜 Licenses & Registrations")
    st.markdown("""
    Add all your business licenses, certifications, and registrations.

    **Why This Matters:**
    - Most tenders require specific licenses (e.g., Trade License, ABC License)
    - Expiry tracking prevents last-minute issues
    - Auto-fills license details in tender forms

    **How to Add a License:**
    1. Click **"Add New License / Registration"**
    2. Select license type
    3. Enter license number and issuing authority
    4. Set issue date and expiry date
    5. Click **"Add License"**

    **Expiry Alerts:** You'll see warnings when licenses are close to expiring:
    - 🟡 **Expiring soon** (within 90 days)
    - 🔴 **EXPIRED** - Take action immediately!
    """)

    # Show license types
    with st.expander("📋 Common License Types", expanded=False):
        st.markdown("""
        | License Type | Purpose | Required For |
        |--------------|---------|--------------|
        | Trade License | Business registration | All tenders |
        | Contractor License | Construction authority | Works tenders |
        | ABC License | Government contractor | Government tenders |
        | Electric License | Electrical works | Electrical tenders |
        | Environment Clearance | Environmental compliance | Large projects |
        | ISO Certificate | Quality management | Quality-sensitive tenders |
        """)

    st.markdown("---")

    # ========================================================================
    # SECTION 3: FINANCIAL DATA
    # ========================================================================
    st.markdown('<a name="financial-data"></a>', unsafe_allow_html=True)
    st.markdown("### 💰 Financial Information")
    st.markdown("""
    Financial data is critical for bid capacity calculation.

    **Key Financial Metrics:**

    | Metric | Description | Why It Matters |
    |--------|-------------|----------------|
    | Annual Turnover | Total revenue | Bid capacity |
    | Construction Turnover | Revenue from construction | Works tenders |
    | Net Worth | Assets - Liabilities | Financial strength |
    | Working Capital | Current Assets - Current Liabilities | Short-term capacity |
    | Liquid Assets | Cash + Marketable securities | Quick liquidity |

    **How to Add Financial Data:**
    1. Click **"Add Financial Record"**
    2. Enter the fiscal year
    3. Fill in your financial metrics
    4. Mark if it's audited
    5. Click **"Add Financial Record"**

    **Pro Tip:** Always keep your financial data updated for accurate bid capacity calculations!
    """)

    # Show financial calculation example
    with st.expander("📊 How Bid Capacity is Calculated", expanded=False):
        st.markdown("""
        **Example Calculation:**
        Annual Turnover: ৳10,000,000
        Working Capital: ৳2,500,000
        Construction Turnover: ৳7,000,000

        Bid Capacity = Working Capital × 2 + (Construction Turnover × 0.1)
        = ৳2,500,000 × 2 + (৳7,000,000 × 0.1)
        = ৳5,000,000 + ৳700,000
        = ৳5,700,000

        text

        This is the maximum tender value you can bid on individually.
        """)

    st.markdown("---")

    # ========================================================================
    # SECTION 4: KEY PERSONNEL
    # ========================================================================
    st.markdown('<a name="personnel"></a>', unsafe_allow_html=True)
    st.markdown("### 👥 Key Personnel")
    st.markdown("""
    Add your key team members who will be involved in tender projects.

    **Who to Add:**
    - Project Managers
    - Site Engineers
    - Technical Specialists
    - Quality Assurance
    - Safety Officers

    **Why This Matters:**
    - Tenders often require team profiles
    - Key personnel must have relevant experience
    - Auto-fills personnel details in forms

    **Features:**
    - ⭐ **Key Personnel** - Mark as key for tender evaluation
    - 🎯 **Prime Candidate** - Highlight your most qualified personnel
    - 📄 **CV Upload** - Attach CVs for easy access
    """)

    # Show personnel fields
    with st.expander("👤 Personnel Profile Fields", expanded=False):
        st.markdown("""
        **Core Information:**
        - Full Name
        - Designation
        - NID Number
        - Phone & Email

        **Qualifications:**
        - Educational Qualification
        - Years of Experience
        - Years with Company
        - Date of Birth

        **Employment:**
        - Present Employer
        - Present Job Title
        - Key Personnel (Yes/No)
        - Prime Candidate (Yes/No)
        """)

    st.markdown("---")

    # ========================================================================
    # SECTION 5: EQUIPMENT
    # ========================================================================
    st.markdown('<a name="equipment"></a>', unsafe_allow_html=True)
    st.markdown("### 🏗️ Equipment Inventory")
    st.markdown("""
    Maintain an inventory of your equipment for tender submissions.

    **Why This Matters:**
    - Works tenders often require equipment lists
    - Shows your capacity to execute projects
    - Auto-fills equipment details in forms

    **Equipment Categories:**
    - 🚜 Excavators
    - 🏗️ Bulldozers
    - 🏋️ Cranes
    - 🚛 Dump Trucks
    - 🔧 Concrete Mixers
    - ⚡ Generators
    - More...

    **Status Tracking:**
    - ✅ Available - Ready for deployment
    - 🔄 Deployed - Currently in use
    - 🔧 Maintenance - In service
    """)

    st.markdown("---")

    # ========================================================================
    # SECTION 6: EXPERIENCE
    # ========================================================================
    st.markdown('<a name="experience"></a>', unsafe_allow_html=True)
    st.markdown("### 📋 Project Experience")
    st.markdown("""
    Document your project history to demonstrate capability.

    **Why This Matters:**
    - Similar experience is often mandatory
    - Shows your project management capabilities
    - Helps in bid evaluation

    **Key Experience Fields:**
    - **Project Name** - Name of the project
    - **Procuring Entity** - Client organization
    - **Contract Value** - Project worth
    - **Award Date** - When work started
    - **Completion Date** - When work finished
    - **Role** - Prime, Subcontractor, or JV Partner

    **Similarity Justification:**
    Explain how this project is similar to the tender you're bidding on.
    This is crucial for tender evaluation!
    """)

    # Show experience metrics
    with st.expander("📊 Experience Dashboard", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Projects", "15", delta="3")
        with col2:
            st.metric("Completed", "12", delta="2")
        with col3:
            st.metric("Total Value", "৳50M", delta="৳10M")

        st.markdown("---")

    # ========================================================================
    # SECTION 7: DOCUMENTS
    # ========================================================================
    st.markdown('<a name="documents"></a>', unsafe_allow_html=True)
    st.markdown("### 📄 Company Documents")
    st.markdown("""
    Store important company documents for easy access.

    **Document Types:**
    - Trade License
    - TIN Certificate
    - VAT Certificate
    - Audit Reports
    - Bank Statements
    - Experience Certificates
    - ISO Certificates

    **Tips for Document Management:**
    1. ✅ **Keep documents current** - Upload new versions when updated
    2. ✅ **Use clear naming** - Make documents easy to find
    3. ✅ **Track expiries** - Set expiry dates for licenses
    4. ✅ **Organize by type** - Group similar documents together
    """)

    st.markdown("---")

    # ========================================================================
    # SECTION 8: CUSTOM FIELD MAPPINGS (MAIN FEATURE)
    # ========================================================================
    st.markdown('<a name="field-mappings"></a>', unsafe_allow_html=True)
    st.markdown("### 🔧 Custom Field Mappings - The Power of Auto-Fill")

    st.markdown("""
    **What is Field Mapping?**

    Field mapping connects form fields in tender documents to your company data.
    When you use the Chrome extension, it automatically fills these fields!
    """)

    # Show how mapping works with a visual diagram
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 10px; border: 2px solid #007bff;">
            <div style="font-size: 1.2rem; font-weight: bold;">🔗 How Field Mapping Works</div>
            <div style="padding: 10px;">
                <div style="background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px;">
                    📋 <strong>Form Field</strong><br>
                    "Company Name"
                </div>
                <div style="font-size: 2rem;">⬇️</div>
                <div style="background: #f3e5f5; padding: 10px; border-radius: 5px; margin: 5px;">
                    🗺️ <strong>Field Mapping</strong><br>
                    companies.company_name
                </div>
                <div style="font-size: 2rem;">⬇️</div>
                <div style="background: #e8f5e9; padding: 10px; border-radius: 5px; margin: 5px;">
                    💾 <strong>Your Data</strong><br>
                    "ABC Construction Ltd"
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Types of mappings
    st.markdown("#### 📊 Types of Field Mappings")

    type_cols = st.columns(2)
    with type_cols[0]:
        st.markdown("""
        **🤖 Automatic (Inferred) Mapping**
        - System automatically detects field types
        - No setup required
        - Uses pattern matching
        - Confidence score: 50-80%

        **Example:** "TIN Number" → companies.tin_number
        """)
    with type_cols[1]:
        st.markdown("""
        **✋ Custom (User-Defined) Mapping**
        - You create the mapping
        - Full control over source data
        - Apply transformation rules
        - Confidence score: 80-100%

        **Example:** "Bid Amount" → company_financials.working_capital
        """)

    st.info("💡 **Best Practice:** Start with automatic mapping, then create custom mappings for fields you use frequently!")

    # How to create a custom mapping
    st.markdown("#### 🛠️ How to Create a Custom Field Mapping")

    step_cols = st.columns([1, 3])
    steps = [
        ("1️⃣", "Go to **Company Profile Management** → **Field Mappings** tab"),
        ("2️⃣", "Select your **Form Type** (e.g., 'Tender Submission')"),
        ("3️⃣", "Click **'Create New Field Mapping'**"),
        ("4️⃣", "Fill in the mapping details:"),
        ("", """
        - **Field ID:** The exact field name in the form
        - **Field Label:** Display name for reference
        - **Source Table:** Which table has the data
        - **Source Column:** Which column to use
        - **Mapping Rule:** How to transform the data
        - **Confidence Score:** How confident are you?
        """),
        ("5️⃣", "Click **'Create Mapping'** and test it!")
    ]

    for icon, text in steps:
        if icon:
            with step_cols[0]:
                st.markdown(f"### {icon}")
            with step_cols[1]:
                st.markdown(text)
        else:
            with st.container():
                st.markdown(text)

    st.markdown("---")

    # Mapping rules
    st.markdown("#### 🔄 Mapping Rules (Transformations)")

    rules_cols = st.columns(2)
    with rules_cols[0]:
        st.markdown("""
        **Text Rules:**
        - `uppercase` → "ABC CONSTRUCTION"
        - `lowercase` → "abc construction"  
        - `title_case` → "Abc Construction"
        - `clean_phone` → "01712345678"
        - `format_nid` → "1234-5678-9012"

        **Join Rules:**
        - `join_with_comma` → "Item1, Item2, Item3"
        """)
    with rules_cols[1]:
        st.markdown("""
        **Formatting Rules:**
        - `format_currency` → "৳1,234,567.00"
        - `format_date` → "25/12/2024"
        - `format_date_english` → "25-12-2024"

        **Calculation Rules:**
        - `calculate_plus_15_percent` → Add 15%
        - `calculate_vat` → Add VAT (15%)
        - `calculate_withholding_tax` → Deduct 10%
        """)

    st.markdown("---")

    # Real-world example
    st.markdown("#### 🎯 Real-World Example: Creating a Field Mapping")

    with st.expander("📝 Step-by-Step Example: Map 'Bid Amount' field", expanded=True):
        st.markdown("""
        **Scenario:** You want to auto-fill the "Bid Amount" field in tender forms.

        1. **Identify the Source Data** - You use `working_capital` from `company_financials`
        2. **Create the Mapping:**
        - Field ID: `bid_amount`
        - Field Label: "Bid Amount"
        - Source Table: `company_financials`
        - Source Column: `working_capital`
        - Mapping Rule: `calculate_plus_15_percent` (Add 15% margin)
        - Confidence Score: `0.9` (90%)

        3. **Test It:** Click "Test Auto-Fill" to verify

        4. **Use It:** When you open a tender form, this field auto-fills!

        **Result:** Your bid amount is automatically calculated from your working capital!
        """)

    st.markdown("---")

    # ========================================================================
    # SECTION 9: AUTO-FILL IN ACTION
    # ========================================================================
    st.markdown('<a name="auto-fill"></a>', unsafe_allow_html=True)
    st.markdown("### ⚡ Auto-Fill in Action")

    st.markdown("""
    **What Auto-Fill Can Do For You:**

    1. **Speed:** Fill forms 10x faster
    2. **Accuracy:** No typos or manual errors  
    3. **Consistency:** Use the same data across tenders
    4. **Efficiency:** Focus on strategy, not data entry

    **How to Use Auto-Fill:**

    #### Option 1: Chrome Extension (Recommended)
    1. Install the TenderAI Chrome Extension
    2. Log in with your credentials
    3. Open a tender form on e-GP or other portals
    4. Click the extension icon
    5. Select "Auto-Fill Form"
    6. 🔗 All mapped fields are filled automatically!

    #### Option 2: Manual Copy
    1. Go to **Company Profile Management**
    2. Copy relevant data
    3. Paste into tender forms

    ### Auto-Fill Confidence Indicators

    | Icon | Meaning | Confidence |
    |------|---------|------------|
    | 🔗 | Custom mapping | 80-100% |
    | 🧠 | Inferred mapping | 50-80% |
    | 📝 | No mapping | 0% (Manual) |
    """)

    # Show auto-fill statistics
    st.markdown("#### 📊 Auto-Fill Usage Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏱️ Time Saved", "~15 min/tender", delta="85% faster")
    with col2:
        st.metric("✅ Accuracy", "99.9%", delta="↑ 25%")
    with col3:
        st.metric("📋 Fields Filled", "25+/tender", delta="↑ 40%")

    st.markdown("---")