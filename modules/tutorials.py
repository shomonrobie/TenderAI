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
    tab_intro, tab_tender, tab_boq, tab_optimize, tab_rates, tab_admin, tab_advanced, tab_extension = st.tabs([
        "🌟 Getting Started",
        "📋 Tender Management",
        "📄 BOQ Generation",
        "🎯 Bid Optimization",
        "🏗️ Rate Management",
        "👑 Admin Guide",
        "⚙️ Advanced Features",
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
    
        


                   
            
            


