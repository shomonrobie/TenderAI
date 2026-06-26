# modules/tender_selector.py

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Tuple, Any
from utils.db_helpers import get_company_tenders_cached


def _normalize_tender_data(tender_data):
    """Convert pandas Series to dict if needed"""
    if tender_data is None:
        return None
    if hasattr(tender_data, 'to_dict'):
        return tender_data.to_dict()
    # If it's already a dict, return as is
    if isinstance(tender_data, dict):
        return tender_data
    return None


def get_tenders_for_company(db, company_id: int, search_term: str = "") -> pd.DataFrame:
    """Get tenders for a company with search filter using cached helper"""
    try:
        if company_id is None:
            print("⚠️ company_id is None, returning empty DataFrame")
            return pd.DataFrame()
        
        company_id = int(company_id)
        print(f"🔍 get_tenders_for_company: company_id={company_id}, search='{search_term}'")
        
        # ✅ FIX: Use the cached helper function
        df = get_company_tenders_cached(company_id)
        
        print(f"   ✅ Retrieved {len(df)} tenders from cache")
        
        # ✅ Apply search filter if provided
        if search_term and not df.empty:
            search_lower = search_term.lower()
            df = df[
                df['tender_id'].str.contains(search_lower, case=False, na=False) |
                df['tender_title'].str.contains(search_lower, case=False, na=False)
            ]
            print(f"   ✅ After search filter: {len(df)} tenders")
        
        # ✅ Ensure data types
        if not df.empty:
            if 'official_estimate' in df.columns:
                df['official_estimate'] = pd.to_numeric(df['official_estimate'], errors='coerce').fillna(0)
            
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            
            # ✅ Debug: Print sample
            print(f"   📋 Sample: {df[['tender_id', 'tender_title']].head(1).to_dict('records')}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error getting tenders: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_tenders_for_company_bak(db, company_id: int, search_term: str = "") -> pd.DataFrame:
    """Get tenders for a company with search filter"""
    try:
        if company_id is None:
            print("⚠️ company_id is None, returning empty DataFrame")
            return pd.DataFrame()
        
        company_id = int(company_id)
        print(f"🔍 get_tenders_for_company: company_id={company_id}, search='{search_term}'")
        
        df = pd.DataFrame()
        
        if hasattr(db, 'get_company_tenders'):
            df = db.get_company_tenders(company_id, search_term)
            print(f"   ✅ Retrieved {len(df)} tenders")
        else:
            with db.get_connection() as conn:
                query = """
                    SELECT id, tender_id, tender_title, procuring_entity, 
                           official_estimate, procurement_type, division, district,
                           submission_deadline, bid_opening_date
                    FROM company_tenders
                    WHERE company_id = ? AND is_active = 1
                """
                params = [company_id]
                
                if search_term:
                    query += " AND (tender_id LIKE ? OR tender_title LIKE ?)"
                    params.extend([f"%{search_term}%", f"%{search_term}%"])
                
                query += " ORDER BY created_at DESC LIMIT 100"
                df = pd.read_sql_query(query, conn, params=params)
        
        # ✅ Ensure data types
        if not df.empty:
            if 'official_estimate' in df.columns:
                df['official_estimate'] = pd.to_numeric(df['official_estimate'], errors='coerce').fillna(0)
            
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            
            for col in ['tender_id', 'tender_title', 'procuring_entity']:
                if col in df.columns:
                    df[col] = df[col].astype(str).fillna('N/A')
        
        return df
        
    except Exception as e:
        print(f"❌ Error getting tenders: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def render_tender_selector(
    db,
    company_id: int,
    search_term: str = "",
    include_manual_entry: bool = True,
    title: str = "📋 Select Tender",
    show_table: bool = True,
    show_summary: bool = True
) -> Tuple[Optional[int], str, float, str, str, str, str]:
    """Reusable tender selector component."""
    
    # ✅ Validate company_id
    if company_id is None:
        st.warning("⚠️ Company ID not found. Please log in again.")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    try:
        company_id = int(company_id)
    except (ValueError, TypeError):
        st.warning("⚠️ Invalid Company ID.")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    st.markdown(f"### {title}")
    
    # ✅ Get tenders using cached helper
    tenders_df = get_tenders_for_company(db, company_id, search_term)
    
    if tenders_df.empty:
        if include_manual_entry:
            return _render_manual_entry()
        else:
            st.info("No tenders found. Please add tenders in Tender Management.")
            return None, None, 0, 'works', None, None, None
    
    # ✅ Display table
    if show_table:
        _render_tender_table(tenders_df)
    
    # ✅ Selection dropdown
    selected = _render_tender_selection(tenders_df)
    
    if not selected:
        st.warning("Please select a tender")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    # ✅ Extract data with proper type conversion
    official_estimate = selected.get('official_estimate', 0)
    try:
        official_estimate = float(official_estimate) if official_estimate else 0
    except (ValueError, TypeError):
        official_estimate = 0
    
    procurement_type = selected.get('procurement_type', 'works')
    selected_tender_id = selected.get('tender_id')  # ✅ Use tender_id
    tender_title = selected.get('tender_title', 'N/A')
    procuring_entity = selected.get('procuring_entity', 'N/A')
    division = selected.get('division', 'Dhaka')
    district = selected.get('district', 'Dhaka')
    
    # ✅ Debug: Print selected
    print(f"📌 Selected: ID={selected_tender_id}, Title={tender_title}, OCE={official_estimate}")
    
    # Show summary
    if show_summary:
        _render_tender_summary(selected)
    
    return selected_tender_id, tender_title, official_estimate, procurement_type, procuring_entity, division, district

def render_tender_selector_bak(
    db,
    company_id: int,
    search_term: str = "",
    include_manual_entry: bool = True,
    title: str = "📋 Select Tender",
    show_table: bool = True,
    show_summary: bool = True
) -> Tuple[Optional[int], str, float, str, str, str, str]:
    """Reusable tender selector component."""
    
    # ✅ Validate company_id
    if company_id is None:
        st.warning("⚠️ Company ID not found. Please log in again.")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    try:
        company_id = int(company_id)
    except (ValueError, TypeError):
        st.warning("⚠️ Invalid Company ID.")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    st.markdown(f"### {title}")
    
    # Get tenders
    tenders_df = get_tenders_for_company(db, company_id, search_term)
    
    if tenders_df.empty:
        if include_manual_entry:
            return _render_manual_entry()
        else:
            st.info("No tenders found. Please add tenders in Tender Management.")
            return None, None, 0, 'works', None, None, None
    
    # Display table
    if show_table:
        _render_tender_table(tenders_df)
    
    # Selection dropdown
    selected = _render_tender_selection(tenders_df)
    
    if not selected:
        st.warning("Please select a tender")
        if include_manual_entry:
            return _render_manual_entry()
        return None, None, 0, 'works', None, None, None
    
    # ✅ Extract data with proper type conversion
    official_estimate = selected.get('official_estimate', 0)
    try:
        official_estimate = float(official_estimate) if official_estimate else 0
    except (ValueError, TypeError):
        official_estimate = 0
    
    procurement_type = selected.get('procurement_type', 'works')
    selected_tender_id = selected.get('tender_id')
    tender_title = selected.get('tender_title', 'N/A')
    procuring_entity = selected.get('procuring_entity', 'N/A')
    division = selected.get('division', 'Dhaka')
    district = selected.get('district', 'Dhaka')
    
    # Show summary
    if show_summary:
        _render_tender_summary(selected)
    
    return selected_tender_id, tender_title, official_estimate, procurement_type, procuring_entity, division, district


def _render_manual_entry() -> Tuple[Optional[int], str, float, str, str, str, str]:
    """Render manual entry for when no tenders exist"""
    st.info("No tenders found. Please add tenders in Tender Management or enter manually.")
    
    # ✅ Initialize variables
    official_estimate = 7500000.0
    procurement_type = 'works'
    tender_title = "Manual Entry"
    procuring_entity = "Manual Entry"
    division = "Dhaka"
    district = "Dhaka"
    
    with st.expander("📝 Manual Entry", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            official_estimate = st.number_input(
                "OCE - BDT", 
                min_value=10000.0, 
                value=official_estimate, 
                step=100000.0, 
                format="%.3f",
                key="manual_oce"
            )
            procurement_type = st.selectbox(
                "Procurement Type", 
                ['goods', 'works', 'services'], 
                index=1,
                key="manual_procurement_type"
            )
        
        with col2:
            tender_title = st.text_input(
                "Tender Title", 
                value=tender_title,
                key="manual_tender_title"
            )
            procuring_entity = st.text_input(
                "Procuring Entity", 
                value=procuring_entity,
                key="manual_procuring_entity"
            )
        
        division = st.selectbox(
            "Division", 
            ["Dhaka", "Chattogram", "Rajshahi", "Khulna", "Barishal", "Sylhet", "Rangpur", "Mymensingh"], 
            index=0,
            key="manual_division"
        )
        district = st.text_input(
            "District", 
            value=district,
            key="manual_district"
        )
    
    return None, tender_title, official_estimate, procurement_type, procuring_entity, division, district

def _render_tender_table(tenders_df: pd.DataFrame):
    """Render formatted tender table - WITHOUT modifying the original DataFrame"""
    
    if tenders_df.empty:
        st.info("No tenders to display")
        return
    
    # ✅ FIX: Create a copy for display only
    display_df = tenders_df.copy()
    
    # ✅ Ensure official_estimate is numeric
    if 'official_estimate' in display_df.columns:
        display_df['official_estimate'] = pd.to_numeric(display_df['official_estimate'], errors='coerce').fillna(0)
    
    # ✅ Format dates if present
    if 'submission_deadline' in display_df.columns:
        display_df['submission_deadline'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce')
        display_df['submission_deadline'] = display_df['submission_deadline'].dt.strftime('%d-%b-%Y')
        display_df['submission_deadline'] = display_df['submission_deadline'].fillna('N/A')
    
    if 'bid_opening_date' in display_df.columns:
        display_df['bid_opening_date'] = pd.to_datetime(display_df['bid_opening_date'], errors='coerce')
        display_df['bid_opening_date'] = display_df['bid_opening_date'].dt.strftime('%d-%b-%Y')
        display_df['bid_opening_date'] = display_df['bid_opening_date'].fillna('N/A')
    
    # ✅ Select and rename columns for display
    display_cols = ['id', 'tender_id', 'tender_title', 'official_estimate', 'submission_deadline', 'bid_opening_date']
    available_cols = [col for col in display_cols if col in display_df.columns]
    
    column_names = {
        'id': 'ID',
        'tender_id': 'Tender ID',
        'tender_title': 'Tender Title',
        'official_estimate': 'OCE (BDT)',
        'submission_deadline': 'Closing Date',
        'bid_opening_date': 'Opening Date'
    }
    
    display_df = display_df[available_cols].rename(columns=column_names)
    
    # ✅ Apply styling
    styled = display_df.style.set_table_styles([
        {'selector': 'thead tr th', 'props': [('background-color', '#1a1a3e'), ('color', 'white'), ('font-weight', 'bold'), ('padding', '10px')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f5f3f8')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#e8e0f0')]},
        {'selector': 'td', 'props': [('padding', '8px')]},
    ])
    
    if 'Tender Title' in display_df.columns:
        styled = styled.set_properties(subset=['Tender Title'], **{'max-width': '300px', 'white-space': 'nowrap', 'overflow': 'hidden', 'text-overflow': 'ellipsis'})
    
    if 'OCE (BDT)' in display_df.columns:
        styled = styled.format({'OCE (BDT)': 'BDT {:,.3f}'})
    
    # ✅ Debug: Print what we're displaying
    print(f"📌 Display table columns: {display_df.columns.tolist()}")
    print(f"📌 Display table data: {display_df.head(1).to_dict('records')}")
    
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True
    )


def _render_tender_table_2(tenders_df: pd.DataFrame):
    """Render formatted tender table"""
    
    if tenders_df.empty:
        st.info("No tenders to display")
        return
    
    # Prepare data
    display_df = tenders_df.copy()
    
    # ✅ Ensure official_estimate is numeric
    if 'official_estimate' in display_df.columns:
        display_df['official_estimate'] = pd.to_numeric(display_df['official_estimate'], errors='coerce').fillna(0)
    
    # ✅ Ensure id is int
    if 'id' in display_df.columns:
        display_df['id'] = pd.to_numeric(display_df['id'], errors='coerce').fillna(0).astype(int)
    
    # ✅ Ensure all string columns are strings and handle NaN
    for col in ['tender_id', 'tender_title', 'procuring_entity', 'division', 'district']:
        if col in display_df.columns:
            # ✅ FIX: Handle NaN values properly
            display_df[col] = display_df[col].fillna('N/A')
            display_df[col] = display_df[col].astype(str).replace('nan', 'N/A')
    
    # ✅ Format dates
    for col in ['submission_deadline', 'bid_opening_date']:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce')
            display_df[col] = display_df[col].dt.strftime('%d-%b-%Y')
            display_df[col] = display_df[col].fillna('N/A')
    
    # Create status column
    if 'status' not in display_df.columns:
        if 'submission_deadline' in display_df.columns:
            now = datetime.now()
            display_df['status'] = display_df['submission_deadline'].apply(
                lambda x: 'Active' if x != 'N/A' and pd.to_datetime(x, format='%d-%b-%Y', errors='coerce') > now else 'Closed'
            )
            display_df['status'] = display_df['status'].fillna('Unknown')
        else:
            display_df['status'] = 'Active'
    
    # ✅ Select columns
    display_cols = ['id', 'tender_id', 'tender_title', 'official_estimate', 'submission_deadline', 'bid_opening_date', 'status']
    available_cols = [col for col in display_cols if col in display_df.columns]
    
    column_names = {
        'id': 'ID',
        'tender_id': 'Tender ID',
        'tender_title': 'Tender Title',
        'official_estimate': 'OCE (BDT)',
        'submission_deadline': 'Closing Date',
        'bid_opening_date': 'Opening Date',
        'status': 'Status'
    }
    
    display_df = display_df[available_cols].rename(columns=column_names)
    
    # ✅ Apply styling
    styled = display_df.style
    
    styled = styled.set_table_styles([
        {'selector': 'thead tr th', 'props': [('background-color', '#1a1a3e'), ('color', 'white'), ('font-weight', 'bold'), ('padding', '10px')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f5f3f8')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#e8e0f0')]},
        {'selector': 'td', 'props': [('padding', '8px')]},
    ])
    
    if 'Tender Title' in display_df.columns:
        styled = styled.set_properties(subset=['Tender Title'], **{'max-width': '300px', 'white-space': 'nowrap', 'overflow': 'hidden', 'text-overflow': 'ellipsis'})
    
    if 'OCE (BDT)' in display_df.columns:
        styled = styled.format({'OCE (BDT)': 'BDT {:,.3f}'})
    
    if 'Status' in display_df.columns:
        def color_status(value):
            if value == 'Active':
                return 'color: #28a745; font-weight: bold;'
            elif value == 'Closed':
                return 'color: #dc3545; font-weight: bold;'
            else:
                return 'color: #ffc107; font-weight: bold;'
        
        styled = styled.applymap(color_status, subset=['Status'])
    
    # ✅ Debug: Print what we're displaying
    print(f"📌 Table columns: {display_df.columns.tolist()}")
    print(f"📌 Sample data: {display_df.head(2).to_dict('records')}")
    
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True
    )


def _render_tender_table_bak(tenders_df: pd.DataFrame):
    """Render formatted tender table"""
    
    if tenders_df.empty:
        st.info("No tenders to display")
        return
    
    # Prepare data
    display_df = tenders_df.copy()
    
    # ✅ Ensure official_estimate is numeric
    if 'official_estimate' in display_df.columns:
        display_df['official_estimate'] = pd.to_numeric(display_df['official_estimate'], errors='coerce').fillna(0)
    
    # ✅ Ensure id is int
    if 'id' in display_df.columns:
        display_df['id'] = pd.to_numeric(display_df['id'], errors='coerce').fillna(0).astype(int)
    
    # ✅ Ensure all string columns are strings
    for col in ['tender_id', 'tender_title', 'procuring_entity', 'division', 'district']:
        if col in display_df.columns:
            display_df[col] = display_df[col].astype(str).fillna('N/A')
    
    # ✅ Format dates
    for col in ['submission_deadline', 'bid_opening_date']:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce')
            display_df[col] = display_df[col].dt.strftime('%d-%b-%Y')
            display_df[col] = display_df[col].fillna('N/A')
    
    # Create status column
    if 'status' not in display_df.columns:
        if 'submission_deadline' in display_df.columns:
            now = datetime.now()
            display_df['status'] = display_df['submission_deadline'].apply(
                lambda x: 'Active' if x != 'N/A' and pd.to_datetime(x, format='%d-%b-%Y', errors='coerce') > now else 'Closed'
            )
            display_df['status'] = display_df['status'].fillna('Unknown')
        else:
            display_df['status'] = 'Active'
    
    # ✅ Select columns
    display_cols = ['id', 'tender_id', 'tender_title', 'official_estimate', 'submission_deadline', 'bid_opening_date', 'status']
    available_cols = [col for col in display_cols if col in display_df.columns]
    
    column_names = {
        'id': 'ID',
        'tender_id': 'Tender ID',
        'tender_title': 'Tender Title',
        'official_estimate': 'OCE (BDT)',
        'submission_deadline': 'Closing Date',
        'bid_opening_date': 'Opening Date',
        'status': 'Status'
    }
    
    display_df = display_df[available_cols].rename(columns=column_names)
    
    # ✅ Apply styling
    styled = display_df.style
    
    styled = styled.set_table_styles([
        {'selector': 'thead tr th', 'props': [('background-color', '#1a1a3e'), ('color', 'white'), ('font-weight', 'bold'), ('padding', '10px')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f5f3f8')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#e8e0f0')]},
        {'selector': 'td', 'props': [('padding', '8px')]},
    ])
    
    if 'Tender Title' in display_df.columns:
        styled = styled.set_properties(subset=['Tender Title'], **{'max-width': '300px', 'white-space': 'nowrap', 'overflow': 'hidden', 'text-overflow': 'ellipsis'})
    
    if 'OCE (BDT)' in display_df.columns:
        styled = styled.format({'OCE (BDT)': 'BDT {:,.3f}'})
    
    if 'Status' in display_df.columns:
        def color_status(value):
            if value == 'Active':
                return 'color: #28a745; font-weight: bold;'
            elif value == 'Closed':
                return 'color: #dc3545; font-weight: bold;'
            else:
                return 'color: #ffc107; font-weight: bold;'
        
        styled = styled.applymap(color_status, subset=['Status'])
    
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True
    )


# modules/tender_selector.py - FIXED _render_tender_selection

def _render_tender_selection(tenders_df: pd.DataFrame) -> Optional[Dict]:
    """Render tender selection dropdown"""
    
    st.markdown("### 📌 Select Tender for Analysis")
    
    if tenders_df.empty:
        st.warning("No tenders available.")
        return None
    
    # ✅ Convert to dict records
    tender_records = tenders_df.to_dict('records')
    
    # ✅ Debug: Print what we received
    print(f"📌 _render_tender_selection: Received {len(tender_records)} records")
    if tender_records:
        print(f"📌 First record: {tender_records[0].get('tender_id')} - {tender_records[0].get('tender_title', '')[:50]}")
    
    # ✅ Validate records
    valid_records = []
    for record in tender_records:
        tender_id = record.get('tender_id')
        if tender_id is None or str(tender_id).strip() == '':
            print(f"   ⚠️ Skipping record with invalid tender_id: {tender_id}")
            continue
        
        # Ensure official_estimate is numeric
        oce = record.get('official_estimate', 0)
        if oce is None or str(oce).lower() == 'nan':
            record['official_estimate'] = 0
        else:
            try:
                record['official_estimate'] = float(oce)
            except (ValueError, TypeError):
                record['official_estimate'] = 0
        
        valid_records.append(record)
    
    print(f"📌 Valid records: {len(valid_records)}")
    
    if not valid_records:
        st.warning("No valid tenders found.")
        return None
    
    return st.selectbox(
        "Choose a tender",
        valid_records,
        format_func=_format_tender_option,
        key="tender_selector"
    )


def _format_tender_option(x: Dict) -> str:
    """Format tender option for dropdown"""
    tender_id = x.get('tender_id', 'N/A')
    title = x.get('tender_title', 'No Title')[:60]
    oce = x.get('official_estimate', 0)
    
    # ✅ FIX: Handle case where tender_id is the column name
    if tender_id == 'tender_id':
        tender_id = 'N/A'
    
    if isinstance(oce, str):
        try:
            oce = float(oce.replace(',', '')) if oce else 0
        except (ValueError, TypeError):
            oce = 0
    
    if not isinstance(oce, (int, float)):
        try:
            oce = float(oce)
        except (ValueError, TypeError):
            oce = 0
    
    return f"{tender_id} - {title} - BDT {oce:,.3f}"

def _render_tender_selection_bak(tenders_df: pd.DataFrame) -> Optional[Dict]:
    """Render tender selection dropdown"""
    
    st.markdown("### 📌 Select Tender for Analysis")
    
    # ✅ Convert to dict with proper types
    tender_records = tenders_df.to_dict('records')
    
    # ✅ Ensure official_estimate is float for each record
    for record in tender_records:
        oce = record.get('official_estimate', 0)
        if isinstance(oce, str):
            try:
                record['official_estimate'] = float(oce.replace(',', '')) if oce else 0
            except (ValueError, TypeError):
                record['official_estimate'] = 0
        elif not isinstance(oce, (int, float)):
            record['official_estimate'] = 0
    
    return st.selectbox(
        "Choose a tender",
        tender_records,
        format_func=_format_tender_option,
        key="tender_selector"
    )


def _format_tender_option_bak(x: Dict) -> str:
    """Format tender option for dropdown"""
    tender_id = x.get('tender_id', 'N/A')
    title = x.get('tender_title', 'No Title')[:60]
    
    oce = x.get('official_estimate', 0)
    if isinstance(oce, str):
        try:
            oce = float(oce.replace(',', '')) if oce else 0
        except (ValueError, TypeError):
            oce = 0
    elif not isinstance(oce, (int, float)):
        oce = 0
    
    return f"{tender_id} - {title} - BDT {oce:,.3f}"


def _render_tender_summary(selected: Dict):
    """Render selected tender summary"""
    
    tender_id = selected.get('tender_id', 'N/A')
    title = selected.get('tender_title', 'N/A')[:60]
    oce = selected.get('official_estimate', 0)
    
    try:
        oce = float(oce) if oce else 0
    except (ValueError, TypeError):
        oce = 0
    
    st.success(f"""
    **Selected Tender:** {tender_id} - {title}
    **OCE:** BDT {oce:,.3f}
    **Procuring Entity:** {selected.get('procuring_entity', 'N/A')}
    **Division:** {selected.get('division', 'N/A')} | **District:** {selected.get('district', 'N/A')}
    """)