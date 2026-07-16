# utils/components.py - Add to existing file

import streamlit as st

def render_tender_styles():
    """Render tender-specific styles"""
    st.markdown("""
    <style>
        /* ===== TENDER DASHBOARD ===== */
        .tender-dashboard-header {
            background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
            padding: 20px 30px;
            border-radius: 12px;
            color: white;
            margin-bottom: 20px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .tender-dashboard-header h1 {
            color: white;
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .tender-dashboard-header .subtitle {
            color: #94a3b8;
            font-size: 14px;
            margin-top: 4px;
        }
        .tender-dashboard-header .badge-container {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .tender-dashboard-header .badge {
            background: rgba(255,255,255,0.1);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            color: #e0e0e0;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .tender-dashboard-header .badge strong {
            color: white;
        }
        
        /* ===== TENDER FILTERS ===== */
        .tender-filters-container {
            background: #1a1a2e;
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid rgba(102, 126, 234, 0.1);
        }
        .tender-filters-container .filter-label {
            color: #94a3b8;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* ===== TENDER TABLE ===== */
        .tender-table-container {
            background: #0f0f23;
            border-radius: 12px;
            border: 1px solid rgba(102, 126, 234, 0.1);
            overflow: hidden;
            margin-top: 10px;
        }
        .tender-table-header {
            display: grid;
            gap: 0;
            padding: 10px 12px;
            background: #1a1a3e;
            border-bottom: 2px solid rgba(102, 126, 234, 0.2);
        }
        .tender-table-header .header-cell {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .tender-table-row {
            display: grid;
            gap: 0;
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            transition: background 0.2s;
            align-items: center;
        }
        .tender-table-row:hover {
            background: rgba(102, 126, 234, 0.05);
        }
        
        /* ===== STATUS BADGES ===== */
        .tender-status-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }
        .tender-status-awarded { background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }
        .tender-status-submitted { background: #f59e0b20; color: #f59e0b; border: 1px solid #f59e0b40; }
        .tender-status-draft { background: #64748b20; color: #94a3b8; border: 1px solid #64748b40; }
        .tender-status-won { background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }
        .tender-status-lost { background: #ef444420; color: #ef4444; border: 1px solid #ef444440; }
        .tender-status-processing { background: #3b82f620; color: #3b82f6; border: 1px solid #3b82f640; }
        .tender-status-under_review { background: #8b5cf620; color: #8b5cf6; border: 1px solid #8b5cf640; }
        
        /* ===== TENDER DETAIL ===== */
        .tender-detail-header {
            background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 100%);
            padding: 20px 30px;
            border-radius: 12px;
            color: white;
            margin-bottom: 20px;
            border: 1px solid rgba(102, 126, 234, 0.2);
        }
        .tender-detail-header h1 {
            color: white;
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .tender-detail-header .subtitle {
            color: #94a3b8;
            font-size: 14px;
            margin-top: 4px;
        }
        .tender-detail-header .meta-row {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 10px;
            font-size: 13px;
            color: #cbd5e1;
        }
        .tender-detail-header .meta-item {
            background: rgba(255,255,255,0.05);
            padding: 4px 12px;
            border-radius: 6px;
        }
        
        /* ===== TENDER PAGINATION ===== */
        .tender-pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            padding: 15px 0;
            flex-wrap: wrap;
        }
        .tender-pagination-container .page-info {
            color: #94a3b8;
            font-size: 13px;
        }
        
        /* ===== TENDER METRIC CARDS ===== */
        .tender-metric-card {
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
        .tender-metric-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .tender-metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }
        .tender-metric-label {
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
    </style>
    """, unsafe_allow_html=True)