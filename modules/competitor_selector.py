# modules/competitor_selector.py

import streamlit as st
import pandas as pd
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = "data/tender_system.db"


def get_competitors_for_company(company_id: int, procurement_type: str = None, search_term: str = "") -> List[Dict[str, Any]]:
    """
    Get competitors for a company, optionally filtered by procurement type.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if procurement_type:
        # Get competitors with bidding history for this procurement type
        cursor.execute("""
            SELECT DISTINCT 
                cm.id,
                cm.competitor_name,
                cm.business_type,
                cm.avg_bid_ratio,
                cm.total_bids,
                cm.total_wins,
                cm.preferred_strategy,
                cm.first_seen,
                cm.last_seen,
                cm.is_active,
                (SELECT COUNT(*) FROM competitor_bids cb 
                 WHERE cb.competitor_name = cm.competitor_name 
                 AND cb.tender_id IN (SELECT tender_id FROM company_tenders WHERE company_id = ? AND procurement_type = ?)
                ) as type_bid_count
            FROM competitor_master cm
            LEFT JOIN competitor_bids cb ON cm.competitor_name = cb.competitor_name
            LEFT JOIN company_tenders ct ON cb.tender_id = ct.tender_id
            WHERE cm.company_id = ? 
              AND cm.is_active = 1
              AND (ct.procurement_type = ? OR ct.procurement_type IS NULL)
            GROUP BY cm.id
            ORDER BY cm.competitor_name
        """, (company_id, procurement_type, company_id, procurement_type))
    else:
        # Get all active competitors
        cursor.execute("""
            SELECT id, competitor_name, business_type, avg_bid_ratio, total_bids, total_wins,
                   preferred_strategy, first_seen, last_seen, is_active
            FROM competitor_master
            WHERE company_id = ? AND is_active = 1
            ORDER BY competitor_name
        """, (company_id,))
    
    competitors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Apply search filter
    if search_term:
        search_lower = search_term.lower()
        competitors = [
            c for c in competitors 
            if search_lower in c.get('competitor_name', '').lower() 
            or search_lower in c.get('business_type', '').lower()
        ]
    
    return competitors


def render_competitor_selector(
    db,
    company_id: int,
    procurement_type: str = None,
    search_term: str = "",
    title: str = "👥 Select Competitors",
    show_table: bool = True,
    multi_select: bool = True,
    max_select: int = 10
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Reusable competitor selector component.
    
    Returns:
        Tuple of (selected_competitors, stats_summary)
    """
    st.markdown(f"### {title}")
    
    if procurement_type:
        st.caption(f"📌 Filtering by procurement type: **{procurement_type.upper()}**")
    
    # Get competitors
    competitors = get_competitors_for_company(company_id, procurement_type, search_term)
    
    if not competitors:
        st.info("No competitors found. Please add competitors in Competitor Master.")
        return [], {'count': 0, 'avg_ratio': 0, 'total_bids': 0}
    
    # Calculate stats
    total_bids = sum(c.get('total_bids', 0) for c in competitors)
    total_wins = sum(c.get('total_wins', 0) for c in competitors)
    avg_ratio = sum(c.get('avg_bid_ratio', 0.92) for c in competitors) / len(competitors) if competitors else 0
    
    stats = {
        'count': len(competitors),
        'avg_ratio': round(avg_ratio, 4),
        'total_bids': total_bids,
        'total_wins': total_wins,
        'win_rate': round(total_wins / total_bids if total_bids > 0 else 0, 4)
    }
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Competitors", stats['count'])
    with col2:
        st.metric("Avg Bid Ratio", f"{stats['avg_ratio']:.3f}")
    with col3:
        st.metric("Total Bids", stats['total_bids'])
    with col4:
        st.metric("Win Rate", f"{stats['win_rate']*100:.0f}%")
    
    st.divider()
    
    # Display table
    if show_table:
        _render_competitor_table(competitors)
    
    # Selection
    if multi_select:
        selected = _render_competitor_multi_select(competitors, max_select)
    else:
        selected = _render_competitor_single_select(competitors)
    
    if selected:
        st.success(f"✅ Selected {len(selected)} competitor(s)")
        selected_names = [c.get('competitor_name', 'Unknown') for c in selected]
        st.caption(f"Competitors: {', '.join(selected_names[:5])}{'...' if len(selected_names) > 5 else ''}")
    
    return selected, stats


def _render_competitor_table(competitors: List[Dict[str, Any]]):
    """Render formatted competitor table"""
    
    if not competitors:
        return
    
    df = pd.DataFrame(competitors)
    
    # Select and rename columns
    display_cols = ['competitor_name', 'business_type', 'avg_bid_ratio', 'total_bids', 'total_wins', 'preferred_strategy']
    available_cols = [col for col in display_cols if col in df.columns]
    
    column_names = {
        'competitor_name': 'Competitor',
        'business_type': 'Business Type',
        'avg_bid_ratio': 'Avg Bid Ratio',
        'total_bids': 'Total Bids',
        'total_wins': 'Total Wins',
        'preferred_strategy': 'Strategy'
    }
    
    display_df = df[available_cols].rename(columns=column_names)
    
    # Format values
    if 'Avg Bid Ratio' in display_df.columns:
        display_df['Avg Bid Ratio'] = display_df['Avg Bid Ratio'].apply(lambda x: f"{x:.3f}")
    
    # ✅ Apply styling
    styled = display_df.style.set_table_styles([
        {'selector': 'thead tr th', 'props': [('background-color', '#1a1a3e'), ('color', 'white'), ('font-weight', 'bold'), ('padding', '10px')]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#f5f3f8')]},
        {'selector': 'tbody tr:hover', 'props': [('background-color', '#e8e0f0')]},
        {'selector': 'td', 'props': [('padding', '8px')]},
    ])
    
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True
    )


def _render_competitor_multi_select(
    competitors: List[Dict[str, Any]], 
    max_select: int = 10
) -> List[Dict[str, Any]]:
    """Render multi-select checkbox list for competitors"""
    
    st.markdown(f"#### Select Competitors (max {max_select})")
    
    selected = []
    
    # Use columns for better layout (3 columns)
    cols = st.columns(3)
    
    for i, comp in enumerate(competitors):
        with cols[i % 3]:
            name = comp.get('competitor_name', 'Unknown')
            ratio = comp.get('avg_bid_ratio', 0)
            label = f"{name} (ratio: {ratio:.3f})"
            
            if st.checkbox(label, key=f"comp_select_{comp.get('id', i)}"):
                selected.append(comp)
            
            if len(selected) >= max_select:
                st.warning(f"Maximum {max_select} competitors selected")
                break
    
    return selected


def _render_competitor_single_select(competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Render single select dropdown for competitors"""
    
    if not competitors:
        return []
    
    selected = st.selectbox(
        "Select a competitor",
        competitors,
        format_func=lambda x: f"{x.get('competitor_name', 'Unknown')} (ratio: {x.get('avg_bid_ratio', 0):.3f})",
        key="competitor_single_select"
    )
    
    return [selected] if selected else []


def get_selected_competitor_bids(
    selected_competitors: List[Dict[str, Any]], 
    official_estimate: float,
    random_factor: float = 0.02
) -> List[float]:
    """Generate bid amounts from selected competitors based on their avg_bid_ratio."""
    
    if not selected_competitors:
        return []
    
    import random
    
    bids = []
    for comp in selected_competitors:
        ratio = comp.get('avg_bid_ratio', 0.92)
        if ratio == 0 or ratio is None:
            ratio = 0.92
        
        noise = 1 + random.uniform(-random_factor, random_factor)
        bid = official_estimate * ratio * noise
        bids.append(round(bid, 3))
    
    return bids