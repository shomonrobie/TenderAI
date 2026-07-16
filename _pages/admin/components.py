"""
Shared UI Components for Admin Dashboard
"""

import streamlit as st
from typing import Dict, Any, List, Optional


def render_common_admin_styles():
    """Render common styles used across admin dashboard"""
    st.markdown("""
    <style>
        /* ===== MAIN HEADER ===== */
        .main-header {
            padding: 0.5rem 0 1rem 0;
            border-bottom: 2px solid #f1f5f9;
            margin-bottom: 1rem;
        }
        .main-header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
        }
        .main-header p {
            font-size: 0.85rem;
            color: #64748b;
            margin: 0.25rem 0 0 0;
        }
        
        /* ===== METRIC CARDS ===== */
        .metric-card {
            background: #f8fafc;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
            height: 80px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .metric-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }
        .metric-label {
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        
        /* ===== STATUS BADGES ===== */
        .status-active {
            color: #065f46;
            background: #d1fae5;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        .status-inactive {
            color: #991b1b;
            background: #fee2e2;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        .status-pending {
            color: #92400e;
            background: #fef3c7;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        .status-trial {
            color: #0369a1;
            background: #e0f2fe;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            display: inline-block;
        }
        
        /* ===== ROLE BADGES ===== */
        .role-badge {
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            background: #f1f5f9;
            color: #475569;
            display: inline-block;
        }
        .role-badge.admin { background: #dbeafe; color: #1e40af; }
        .role-badge.manager { background: #d1fae5; color: #065f46; }
        .role-badge.analyst { background: #fef3c7; color: #92400e; }
        .role-badge.estimator { background: #d1ecf1; color: #0c5460; }
        .role-badge.system { background: #e0e7ff; color: #4338ca; }
        .role-badge.viewer { background: #f1f5f9; color: #475569; }
        
        /* ===== GRID TABLE ===== */
        .grid-container {
            background: white;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            overflow: hidden;
            padding: 0.25rem 0;
        }
        .grid-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #f1f5f9;
            background: #fafbfc;
        }
        .grid-title {
            font-size: 1rem;
            font-weight: 600;
            color: #0f172a;
        }
        .grid-row {
            display: flex;
            align-items: center;
            padding: 0.5rem 1rem;
            border-bottom: 1px solid #f8fafc;
            transition: background 0.15s ease;
            cursor: pointer;
        }
        .grid-row:hover {
            background: #f8fafc;
        }
        .grid-row.selected {
            background: #eef2ff;
            border-left: 4px solid #6366f1;
        }
        .grid-row:last-child {
            border-bottom: none;
        }
        .grid-pagination {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            border-top: 1px solid #f1f5f9;
            background: #fafbfc;
        }
        .grid-pagination-info {
            font-size: 0.8rem;
            color: #64748b;
        }
        
        /* ===== DETAIL VIEW ===== */
        .detail-container {
            background: white;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            padding: 1.5rem;
        }
        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        .detail-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #0f172a;
        }
        .detail-section {
            margin-bottom: 1.5rem;
        }
        .detail-section-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 0.5rem;
        }
        .detail-back-btn {
            background: none;
            border: 1px solid #e2e8f0;
            padding: 0.35rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            color: #475569;
        }
        .detail-back-btn:hover {
            background: #f1f5f9;
        }
        
        /* ===== ACTION BUTTONS ===== */
        .action-btn {
            background: transparent;
            border: none;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            color: #64748b;
        }
        .action-btn:hover {
            background: #f1f5f9;
        }
        .action-btn.danger:hover {
            background: #fee2e2;
            color: #ef4444;
        }
        
        /* ===== FORM STYLES ===== */
        .form-section {
            margin-bottom: 1.5rem;
        }
        .form-section-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 0.5rem;
        }
        
        /* ===== PLAN CARDS ===== */
        .plan-card {
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            height: 100%;
            transition: all 0.2s ease;
        }
        .plan-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        }
        .plan-card.popular {
            border: 2px solid #6366f1;
            background: #f8fafc;
        }
        .plan-card.default {
            border: 2px solid #e2e8f0;
            background: white;
        }
        .plan-card.current {
            border: 2px solid #10b981;
            background: #f0fdf4;
        }
        .plan-name {
            font-size: 1.1rem;
            font-weight: 600;
            color: #0f172a;
            margin: 0;
        }
        .plan-price {
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
            margin: 8px 0;
        }
        .plan-price-period {
            font-size: 14px;
            font-weight: 400;
            color: #94a3b8;
        }
        .plan-features {
            text-align: left;
            margin: 12px 0;
            font-size: 12px;
        }
        .plan-feature {
            padding: 2px 0;
        }
        .plan-badge {
            background: #6366f1;
            color: white;
            padding: 2px 12px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 8px;
        }
        .plan-current-badge {
            background: #10b981;
            color: white;
            padding: 2px 12px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            display: inline-block;
            margin-top: 8px;
        }
        
        /* ===== RESPONSIVE ===== */
        @media (max-width: 1200px) {
            .metric-value { font-size: 1.25rem; }
            .metric-card { height: 70px; padding: 0.5rem 0.75rem; }
        }
        @media (max-width: 768px) {
            .metric-card { height: 60px; }
            .metric-value { font-size: 1rem; }
            .metric-label { font-size: 0.6rem; }
        }
    </style>
    """, unsafe_allow_html=True)


def render_metric_row(metrics: Dict[str, Any]):
    """Render metric cards row"""
    cols = st.columns(6)
    
    metric_configs = [
        {"key": "total_users", "icon": "📊", "label": "Total Users"},
        {"key": "active_users", "icon": "👥", "label": "Active Users"},
        {"key": "companies", "icon": "🏢", "label": "Companies"},
        {"key": "paid_subs", "icon": "💰", "label": "Paid Subscriptions"},
        {"key": "total_analyses", "icon": "📈", "label": "Analyses"},
        {"key": "revenue", "icon": "💵", "label": "Revenue"}
    ]
    
    for idx, config in enumerate(metric_configs):
        value = metrics.get(config["key"], 0)
        
        if config["key"] == "revenue":
            display = f"${value:,.2f}"
        else:
            display = f"{value:,}"
        
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-card">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.25rem;">{config['icon']}</span>
                    <div>
                        <div class="metric-value">{display}</div>
                        <div class="metric-label">{config['label']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_grid_pagination(current_page: int, total_pages: int, total_records: int, start_idx: int, end_idx: int, prefix: str = ""):
    """Render pagination controls for grid view"""
    if total_pages <= 1:
        return
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
    
    with col1:
        if st.button("◀ Prev", key=f"{prefix}_prev_page", disabled=(current_page <= 1), use_container_width=True):
            st.session_state[f"{prefix}_page"] = current_page - 1
            st.rerun()
    
    with col2:
        st.markdown(f"<div style='text-align: center; padding-top: 6px; color: #475569;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
    
    with col3:
        page_cols = st.columns(min(total_pages, 7))
        start_page = max(1, current_page - 3)
        end_page = min(total_pages, current_page + 3)
        
        for i, p in enumerate(range(start_page, end_page + 1)):
            with page_cols[i]:
                if st.button(str(p), key=f"{prefix}_page_{p}", 
                            type="primary" if p == current_page else "secondary",
                            use_container_width=True):
                    st.session_state[f"{prefix}_page"] = p
                    st.rerun()
    
    with col4:
        jump_to = st.number_input(
            "Jump to",
            min_value=1,
            max_value=total_pages,
            value=current_page,
            step=1,
            key=f"{prefix}_jump_to",
            label_visibility="collapsed"
        )
        if jump_to != current_page:
            st.session_state[f"{prefix}_page"] = jump_to
            st.rerun()
    
    with col5:
        if st.button("Next ▶", key=f"{prefix}_next_page", disabled=(current_page >= total_pages), use_container_width=True):
            st.session_state[f"{prefix}_page"] = current_page + 1
            st.rerun()
    
    st.caption(f"Showing {start_idx + 1}–{end_idx} of {total_records} records")