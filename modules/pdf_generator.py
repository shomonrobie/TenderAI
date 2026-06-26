# modules/pdf_generator.py
import io
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager
import traceback
from matplotlib.patches import Wedge, Circle
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configure matplotlib for non-interactive backend (server-friendly)
plt.switch_backend('Agg')

def debug_print(*args, **kwargs):
    print(*args, **kwargs)

DEBUG_MODE = True  # Set to False in production
db = UnifiedDatabaseManager()

# =============================================================================
# 📊 PLOT GENERATION FUNCTIONS
# =============================================================================

def _create_tier_comparison_chart(comparison: dict, est: float = None) -> io.BytesIO:
    """Create bar chart comparing win probability and confidence across tiers"""
    if not comparison:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 4))
    
    tiers = []
    win_probs = []
    confidence_scores = []
    
    for tier in ['basic', 'advanced', 'enhanced']:
        if tier in comparison:
            data = comparison[tier]
            tiers.append(tier.upper())
            win_probs.append(data.get('win_probability', 0) * 100)
            confidence_scores.append(data.get('confidence_score', 0) * 100)
    
    if not tiers:
        plt.close(fig)
        return None
    
    x = range(len(tiers))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], win_probs, width, 
                   label='Win Probability', color='#2563eb', alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], confidence_scores, width, 
                   label='Confidence Score', color='#10b981', alpha=0.8)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.0f}%', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.0f}%', ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel('Percentage (%)', fontsize=10)
    ax.set_title('Three-Tier Analysis: Win Probability vs Confidence', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tiers)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')
    
    return _fig_to_imagerenderer(fig)

def _create_ppr_gauge_chart(est: float, recommended_bid: float, slt: float) -> io.BytesIO:
    """Create a gauge chart similar to your Plotly one but as PNG for PDF"""
        
    fig, ax = plt.subplots(figsize=(6, 3))
    
    # Calculate compliance percentage
    compliance_pct = min(100, max(0, (recommended_bid / slt) * 100)) if slt > 0 else 0
    
    # Create gauge
    colors_list = ['#fee2e2', '#dcfce7']
    
    # Simple horizontal gauge
    ax.barh(['SLT Threshold', 'Recommended Bid'], [slt, recommended_bid], 
            color=['#ef4444', '#10b981'], alpha=0.7)
    
    # Add value labels
    ax.text(slt + (max(slt, recommended_bid) * 0.02), 0, f'BDT {slt:,.0f}', 
            va='center', fontsize=10)
    ax.text(recommended_bid + (max(slt, recommended_bid) * 0.02), 1, f'BDT {recommended_bid:,.0f}', 
            va='center', fontsize=10)
    
    # Add compliance indicator
    status = "✅ COMPLIANT" if recommended_bid >= slt else "⚠️ BELOW SLT"
    status_color = '#10b981' if recommended_bid >= slt else '#ef4444'
    
    ax.text(0.5, -0.3, f'{status} | {compliance_pct:.0f}% of SLT', 
            transform=ax.transAxes, ha='center', fontsize=11, 
            fontweight='bold', color=status_color)
    
    ax.set_xlim(0, max(slt, recommended_bid) * 1.1)
    ax.set_xlabel('Amount (BDT)')
    ax.set_title('PPR 2025 Compliance: Recommended Bid vs SLT Threshold', fontsize=12, fontweight='bold')
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_format_bdt_axis))
    
    plt.tight_layout()
    return _fig_to_imagerenderer(fig)


def _create_ppr_calculation_table(est: float, nppi: float, slt: float, recommended_bid: float, 
                                    competitor_bids: list = None, ppr_metrics: dict = None) -> Table:
    """Create detailed PPR 2025 calculation breakdown table with proper text wrapping"""
    
    
    
    styles = getSampleStyleSheet()
    
    # Create a style for wrapped text
    wrap_style = ParagraphStyle(
        'WrapStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        alignment=0,  # Left aligned
        wordWrap='CJK'  # Enable word wrapping
    )
    
    # Style for formula column (can be multi-line)
    formula_style = ParagraphStyle(
        'FormulaStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        alignment=0,
        wordWrap='CJK'
    )
    
    if ppr_metrics:
        avg_comp = ppr_metrics.get('avg_competitor', 0)
        weighted_avg = ppr_metrics.get('weighted_average', 0)
        weighted_std = ppr_metrics.get('weighted_std_dev', 0)
        nppi_price = ppr_metrics.get('nppi_price', est * nppi)
    else:
        comp_values = [c.get('bid', 0) for c in (competitor_bids or []) if c.get('bid', 0) > 0]
        avg_comp = sum(comp_values) / len(comp_values) if comp_values else 0
        nppi_price = est * nppi
        weighted_avg = (0.5 * avg_comp) + (0.2 * est) + (0.3 * nppi_price) if avg_comp > 0 else est * 0.85
        weighted_std = np.std(comp_values) if len(comp_values) > 1 else est * 0.05
    
    # Build calculation steps with proper text wrapping
    calc_data = [
        ["Step", "Formula / Description", "Calculation", "Result (BDT)"],
        
        ["1", 
         Paragraph("Official Estimate<br/><font size='7' color='#666'>From tender document</font>", wrap_style),
         Paragraph(f"<b>{est:,.0f}</b>", wrap_style),
         "Base Value"],
        
        ["2", 
         Paragraph("NPPI Factor<br/><font size='7' color='#666'>28-day market average</font>", wrap_style),
         Paragraph(f"<b>{nppi:.3f}</b>", wrap_style),
         "Index Factor"],
        
        ["3", 
         Paragraph("NPPI Price<br/><font size='7' color='#666'>Estimate × NPPI Factor</font>", wrap_style),
         Paragraph(f"{est:,.0f} × {nppi:.3f}", wrap_style),
         Paragraph(f"<b>{nppi_price:,.0f}</b>", wrap_style)],
        
        ["4", 
         Paragraph("Avg Competitor<br/><font size='7' color='#666'>Σ(Comp Bids) ÷ N</font>", wrap_style),
         Paragraph(f"({len(competitor_bids or [])} bids)", wrap_style),
         Paragraph(f"<b>{avg_comp:,.0f}</b>" if avg_comp > 0 else "N/A", wrap_style)],
        
        ["5", 
         Paragraph("Weighted Avg (X̄)<br/><font size='7' color='#666'>0.5(Avg) + 0.2(Est) + 0.3(NPPI)</font>", wrap_style),
         Paragraph(f"0.5×{avg_comp:,.0f}<br/>+ 0.2×{est:,.0f}<br/>+ 0.3×{nppi_price:,.0f}", formula_style),
         Paragraph(f"<b>{weighted_avg:,.0f}</b>", wrap_style)],
        
        ["6", 
         Paragraph("Std Deviation (Sd)<br/><font size='7' color='#666'>√[Σ(x̄ - xᵢ)²/(n-1)]</font>", wrap_style),
         Paragraph(f"σ = {weighted_std:.2f}", wrap_style),
         Paragraph(f"<b>{weighted_std:,.0f}</b>", wrap_style)],
        
        ["7", 
         Paragraph("SLT Threshold<br/><font size='7' color='#666'>X̄ - Sd</font>", wrap_style),
         Paragraph(f"{weighted_avg:,.0f} - {weighted_std:,.0f}", wrap_style),
         Paragraph(f"<b>{slt:,.0f}</b>", wrap_style)],
        
        ["8", 
         Paragraph("Recommended Bid<br/><font size='7' color='#666'>AI Optimized</font>", wrap_style),
         Paragraph("Based on win probability", wrap_style),
         Paragraph(f"<b>{recommended_bid:,.0f}</b>", wrap_style)],
        
        ["9", 
         Paragraph("Compliance Check<br/><font size='7' color='#666'>Bid ≥ SLT?</font>", wrap_style),
         Paragraph(f"{recommended_bid:,.0f} ≥ {slt:,.0f}", wrap_style),
         Paragraph(f"<b>{'✅ PASS' if recommended_bid >= slt else '❌ FAIL'}</b>", wrap_style)],
    ]
    
    # Calculate dynamic column widths (wider for formula and value columns)
    # Column widths: Step(0.4"), Formula(2.2"), Value(1.8"), Result(1.2")
    table = Table(calc_data, colWidths=[0.4*inch, 2.2*inch, 1.8*inch, 1.2*inch], repeatRows=1)
    
    # Apply table styling
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        
        # Data rows styling
        ('BACKGROUND', (0,1), (-1,-2), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#dcfce7') if recommended_bid >= slt else colors.HexColor('#fee2e2')),
        
        # Grid lines
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        
        # Cell alignment and padding
        ('ALIGN', (0,1), (0,-1), 'CENTER'),  # Step column center aligned
        ('ALIGN', (1,1), (1,-1), 'LEFT'),     # Formula column left aligned
        ('ALIGN', (2,1), (2,-1), 'LEFT'),     # Value column left aligned
        ('ALIGN', (3,1), (3,-1), 'RIGHT'),    # Result column right aligned
        
        ('VALIGN', (0,1), (-1,-1), 'TOP'),     # Top alignment for all cells
        
        # Padding for all cells
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
        ('LEFTPADDING', (0,1), (-1,-1), 6),
        ('RIGHTPADDING', (0,1), (-1,-1), 6),
        
        # Font settings for data rows
        ('FONTSIZE', (0,1), (-1,-1), 8),
        
        # Zebra striping for better readability
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.HexColor('#ffffff'), colors.HexColor('#f1f5f9')]),
    ]))
    
    return table


def _create_competitor_chart(comp_bids: list, recommended_bid: float, est: float) -> io.BytesIO:
    """Create horizontal bar chart of competitor bids"""
    if not comp_bids:
        return None
    
    # Limit to 12 competitors for readability
    comp_bids = comp_bids[:12]
    
    fig_height = max(4, len(comp_bids) * 0.4)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    
    comp_names = []
    comp_bid_values = []
    
    for i, comp in enumerate(comp_bids, 1):
        name = comp.get('name', f'Competitor {i}')
        if len(name) > 25:
            name = name[:22] + '...'
        comp_names.append(name)
        comp_bid_values.append(comp.get('bid', 0))
    
    # Sort by bid amount (descending)
    sorted_data = sorted(zip(comp_names, comp_bid_values), key=lambda x: x[1], reverse=True)
    if sorted_data:
        comp_names, comp_bid_values = zip(*sorted_data)
    else:
        comp_names, comp_bid_values = [], []
    
    # Create horizontal bar chart
    y_pos = range(len(comp_names))
    bars = ax.barh(y_pos, comp_bid_values, color='#ef4444', alpha=0.7)
    
    # Highlight recommended bid
    if recommended_bid > 0:
        ax.axvline(x=recommended_bid, color='#2563eb', linestyle='--', linewidth=2, 
                  label=f'Recommended: BDT {recommended_bid:,.0f}')
    
    # Add value labels
    for bar, val in zip(bars, comp_bid_values):
        ax.text(val, bar.get_y() + bar.get_height()/2, 
               f' BDT {val:,.0f}', va='center', fontsize=8)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(comp_names)
    ax.set_xlabel('Bid Amount (BDT)', fontsize=10)
    ax.set_title('Competitor Bid Distribution', fontsize=12, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3, axis='x')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_format_bdt_axis))
    
    return _fig_to_imagerenderer(fig)




def _create_risk_radar_chart(comparison: dict, slt: float) -> io.BytesIO:
    """Create radar chart for risk assessment across tiers"""
    if not comparison:
        return None
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection='polar'))
    
    metrics = ['Win Probability', 'Confidence', 'PPR Compliance', 'Cost Efficiency', 'Risk Score']
    
    tier_data = {}
    for tier in ['basic', 'advanced', 'enhanced']:
        if tier in comparison:
            data = comparison[tier]
            values = [
                data.get('win_probability', 0.5) * 100,
                data.get('confidence_score', 0.5) * 100,
                100 if data.get('optimal_bid', 0) >= slt else 50,
                min(100, (data.get('bid_ratio', 1) * 100)),
                100 - (data.get('confidence_score', 0.5) * 100)
            ]
            tier_data[tier.upper()] = values
    
    if not tier_data:
        plt.close(fig)
        return None
    
    angles = [n / float(len(metrics)) * 2 * np.pi for n in range(len(metrics))]
    angles += angles[:1]
    
    colors_list = ['#2563eb', '#10b981', '#f59e0b']
    
    for idx, (tier, values) in enumerate(tier_data.items()):
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, label=tier, 
               color=colors_list[idx % len(colors_list)])
        ax.fill(angles, values, alpha=0.1, color=colors_list[idx % len(colors_list)])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title('Risk & Performance Radar Chart', fontsize=12, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax.grid(True)
    
    return _fig_to_imagerenderer(fig)



def _create_profit_scenario_chart(est: float, recommended_bid: float, slt: float) -> io.BytesIO:
    """Create scenario analysis for profit at different bid levels"""
    if est <= 0:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Generate bid range (75% to 105% of estimate)
    bid_range = np.linspace(est * 0.75, est * 1.05, 50)
    
    # Estimate cost (assuming 85% of estimate)
    estimated_cost = est * 0.85
    
    # Calculate profit for each bid level
    profits = bid_range - estimated_cost
    
    # Calculate win probability curve (simplified logistic model)
    win_prob_curve = 1 / (1 + np.exp((bid_range - est) / (est * 0.1)))
    
    # Expected value = profit * win_probability
    expected_value = profits * win_prob_curve
    
    # Plot
    ax.plot(bid_range, profits, label='Profit if Win', color='#10b981', linewidth=2)
    ax.plot(bid_range, expected_value, label='Expected Value', color='#f59e0b', linewidth=2, linestyle='--')
    
    # Mark recommended bid
    if recommended_bid > 0:
        ax.axvline(x=recommended_bid, color='red', linestyle=':', linewidth=2, alpha=0.7, 
                  label=f'Recommended: BDT {recommended_bid:,.0f}')
    
    # Mark SLT threshold
    if slt > 0:
        ax.axvline(x=slt, color='orange', linestyle=':', linewidth=2, alpha=0.7, 
                  label=f'SLT Threshold: BDT {slt:,.0f}')
    
    ax.set_xlabel('Bid Amount (BDT)', fontsize=10)
    ax.set_ylabel('Amount (BDT)', fontsize=10)
    ax.set_title('Profit Scenario Analysis', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_format_bdt_axis))
    
    return _fig_to_imagerenderer(fig)


def _create_win_probability_curve(est: float, recommended_bid: float, competitor_bids: list) -> io.BytesIO:
    """Create win probability curve based on competitor distribution"""
    if est <= 0:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Generate bid range
    bid_range = np.linspace(est * 0.7, est * 1.1, 100)
    
    # Calculate win probability based on competitor bids
    if competitor_bids:
        comp_values = [c.get('bid', 0) for c in competitor_bids if c.get('bid', 0) > 0]
        if comp_values:
            # Use competitor distribution to model win probability
            win_probs = []
            for bid in bid_range:
                # Probability of winning = proportion of competitors with higher bids
                if bid <= min(comp_values) * 0.9:
                    win_probs.append(0.95)
                elif bid >= max(comp_values) * 1.1:
                    win_probs.append(0.05)
                else:
                    below_count = sum(1 for c in comp_values if c >= bid)
                    win_probs.append(below_count / len(comp_values))
            win_probs = np.array(win_probs)
        else:
            # Fallback to logistic curve
            win_probs = 1 / (1 + np.exp((bid_range - est) / (est * 0.15)))
    else:
        # Default logistic curve
        win_probs = 1 / (1 + np.exp((bid_range - est) / (est * 0.15)))
    
    ax.plot(bid_range, win_probs * 100, color='#2563eb', linewidth=2)
    ax.fill_between(bid_range, win_probs * 100, alpha=0.3, color='#2563eb')
    
    # Mark recommended bid
    if recommended_bid > 0:
        idx = np.argmin(np.abs(bid_range - recommended_bid))
        win_at_rec = win_probs[idx] * 100
        ax.plot(recommended_bid, win_at_rec, 'ro', markersize=8)
        ax.annotate(f'Win Probability: {win_at_rec:.0f}%', 
                   xy=(recommended_bid, win_at_rec),
                   xytext=(recommended_bid + est*0.05, win_at_rec + 10),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=8)
    
    ax.set_xlabel('Bid Amount (BDT)', fontsize=10)
    ax.set_ylabel('Win Probability (%)', fontsize=10)
    ax.set_title('Win Probability Curve', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_format_bdt_axis))
    
    return _fig_to_imagerenderer(fig)



def _fig_to_imagerenderer(fig) -> io.BytesIO:
    """Convert matplotlib figure to BytesIO buffer for ReportLab Image"""
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer  # Return BytesIO, not ImageReader



def _format_bdt_axis(x, p):
    """Format axis labels for BDT amounts"""
    if x >= 1e7:
        return f'BDT {x/1e7:.1f}Cr'
    elif x >= 1e6:
        return f'BDT {x/1e6:.1f}M'
    elif x >= 1e3:
        return f'BDT {x/1e3:.0f}K'
    return f'BDT {x:.0f}'


# =============================================================================
# 📄 MAIN PDF GENERATION FUNCTIONS
# =============================================================================

def generate_babui_detailed_report(report_data: dict, user_info: dict = None, include_charts: bool = True) -> io.BytesIO:
    """
    Generates a comprehensive, print-ready PDF report for TenderAI.
    Handles missing data gracefully and includes all requested sections with optional charts.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # ─── Custom Styles ───────────────────────────────────────────────────────
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, 
                                 textColor=colors.HexColor('#0f172a'), alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=13, 
                                   textColor=colors.HexColor('#2563eb'), alignment=TA_CENTER, 
                                   spaceAfter=16, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, 
                                  textColor=colors.HexColor('#1e40af'), spaceBefore=14, 
                                  spaceAfter=6, fontName='Helvetica-Bold')
    normal_style = styles['Normal']

    # ─── Safe Data Extraction ────────────────────────────────────────────────
    def safe_float(val, default=0.0):
        try: 
            return float(val) if val is not None else default
        except: 
            return default
    
    def safe_str(val, default="N/A"):
        return str(val).strip() if val is not None and str(val).strip() else default

    est = safe_float(report_data.get('official_estimate', 1), 1.0)
    bid = safe_float(report_data.get('recommended_bid', 0), 0.0)
    slt = safe_float(report_data.get('slt_threshold', est * 0.8), est * 0.8)
    nppi = safe_float(report_data.get('nppi_factor', 0.92), 0.92)
    win_prob = safe_float(report_data.get('success_probability', 0.6), 0.6)
    comp_count = int(safe_float(report_data.get('competitor_count', len(report_data.get('competitor_bids', [])))))
    bid_source = safe_str(report_data.get('bid_source', 'Auto-Generated'))
    risk_tol = safe_str(report_data.get('risk_tolerance', 'moderate')).title()
    comparison = report_data.get('comparison', {})
    comp_bids = report_data.get('competitor_bids', [])

    # ─── HEADER ─────────────────────────────────────────────────────────────
    story.append(Paragraph("🤖 TenderAI", title_style))
    story.append(Paragraph("AI Enhanced Bid Management System", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Analysis ID: {report_data.get('id', 'N/A')}",
                           ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 12))

    # ─── TENDER INFORMATION ──────────────────────────────────────────────────
    story.append(Paragraph("📋 Tender Information", section_style))
    info_data = [
        ["Tender ID", safe_str(report_data.get('tender_id')), "Procuring Entity", safe_str(report_data.get('procuring_entity'))],
        ["Official Estimate", f"BDT {est:,.3f}", "Procurement Type", safe_str(report_data.get('procurement_type', 'goods')).upper()],  # ✅ 3 decimals
        ["Submission Deadline", safe_str(report_data.get('submission_deadline', 'N/A'))[:10], "Risk Tolerance", risk_tol],
        ["Location", f"{safe_str(report_data.get('division', ''))} / {safe_str(report_data.get('district', ''))}", "Competitors", f"{comp_count} ({bid_source})"]
    ]


    info_table = Table(info_data, colWidths=[1.4*inch, 1.8*inch, 1.4*inch, 1.8*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ─── AI RECOMMENDATIONS ──────────────────────────────────────────────────
    story.append(Paragraph("🎯 AI Recommendations", section_style))
    rec_text = (
        f"Based on {comp_count} competitor bids and PPR 2025 compliance metrics, the optimal bid is "
        f"<b>BDT {bid:,.3f}</b> ({bid/est*100:.1f}% of estimate). This bid maintains a "  # ✅ 3 decimals
        f"<b>{win_prob*100:.0f}%</b> win probability while staying safely above the SLT threshold of "
        f"BDT {slt:,.3f}. Risk assessment indicates a <b>" + safe_str(report_data.get('risk_level', 'MEDIUM')) + "</b> risk profile."  # ✅ 3 decimals
    )
    story.append(Paragraph(rec_text, ParagraphStyle('Rec', parent=normal_style, fontSize=10, spaceAfter=8)))
    story.append(Spacer(1, 8))

    # ─── VISUAL CHARTS (NEW - Optional) ──────────────────────────────────────
    if include_charts:
        story.append(Paragraph("📊 Visual Performance Dashboard", section_style))
        
        # Chart 1: Tier Comparison
        tier_chart = _create_tier_comparison_chart(comparison, est)
        if tier_chart:
            story.append(Paragraph("<b>Figure 1:</b> Three-Tier Performance Comparison", 
                                  ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
            story.append(ReportLabImage(tier_chart, width=6*inch, height=3.5*inch))
            story.append(Spacer(1, 8))
        
        # Chart 2: Competitor Distribution
        comp_chart = _create_competitor_chart(comp_bids, bid, est)
        if comp_chart:
            story.append(Paragraph("<b>Figure 2:</b> Competitor Bid Analysis", 
                                  ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
            story.append(ReportLabImage(comp_chart, width=6*inch, height=max(3*inch, len(comp_bids) * 0.3 * inch)))
            story.append(Spacer(1, 8))
        
        # Chart 3: Win Probability Curve
        win_chart = _create_win_probability_curve(est, bid, comp_bids)
        if win_chart:
            story.append(Paragraph("<b>Figure 3:</b> Win Probability Analysis", 
                                  ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
            story.append(ReportLabImage(win_chart, width=6*inch, height=3.5*inch))
            story.append(Spacer(1, 8))
        
        # Charts 4 & 5: Side-by-side (Risk Radar + Profit Scenario)
        risk_chart = _create_risk_radar_chart(comparison, slt)
        profit_chart = _create_profit_scenario_chart(est, bid, slt)
        
        if risk_chart or profit_chart:
            story.append(Paragraph("<b>Figures 4 & 5:</b> Risk & Financial Analysis", 
                                  ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
            
            if risk_chart and profit_chart:
                # Two-column layout for side-by-side charts
                chart_table_data = [
                    [ReportLabImage(risk_chart, width=3*inch, height=3*inch),
                     ReportLabImage(profit_chart, width=3.5*inch, height=2.5*inch)]
                ]
                chart_table = Table(chart_table_data, colWidths=[3.2*inch, 3.2*inch])
                chart_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))
                story.append(chart_table)
            elif risk_chart:
                story.append(ReportLabImage(risk_chart, width=5*inch, height=5*inch))
            elif profit_chart:
                story.append(ReportLabImage(profit_chart, width=6*inch, height=3.5*inch))
            
            story.append(Spacer(1, 12))

    # ─── THREE-TIER ANALYSIS COMPARISON ──────────────────────────────────────
    story.append(Paragraph("📊 Three-Tier Analysis Comparison", section_style))
    tier_rows = [["Tier", "Method", "Optimal Bid (BDT)", "Win Prob (%)", "Confidence (%)", "Risk"]]
    for tier in ['basic', 'advanced', 'enhanced']:
        if tier in comparison:
            r = comparison[tier]
            tier_rows.append([
                tier.upper(),
                safe_str(r.get('method', '')),
                f"{safe_float(r.get('optimal_bid', 0)):,.3f}",  # ✅ 3 decimals
                f"{safe_float(r.get('win_probability', 0))*100:.0f}%",
                f"{safe_float(r.get('confidence_score', 0.7))*100:.0f}%",
                safe_str(r.get('risk_level', 'N/A'))
            ])
    tier_table = Table(tier_rows, colWidths=[1*inch, 1.3*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
    tier_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5)
    ]))
    story.append(tier_table)
    story.append(Spacer(1, 12))

    # ─── COMPETITOR INTELLIGENCE ─────────────────────────────────────────────
    story.append(Paragraph("👥 Competitor Intelligence", section_style))
    if comp_bids:
        comp_rows = [["Competitor", "Bid Amount (BDT)", "% of Estimate", "Deviation"]]
        for i, cb in enumerate(comp_bids, 1):
            cb_bid = safe_float(cb.get('bid', 0))
            pct = (cb_bid / est * 100) if est > 0 else 0
            dev = ((cb_bid - est) / est * 100) if est > 0 else 0
            comp_rows.append([
                safe_str(cb.get('name', f'Competitor {i}')),
                f"{cb_bid:,.3f}",
                f"{pct:.1f}%",
                f"{dev:+.1f}%"
            ])
        comp_table = Table(comp_rows, colWidths=[1.8*inch, 1.5*inch, 1*inch, 1*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0fdf4')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5)
        ]))
        story.append(comp_table)
    else:
        story.append(Paragraph("No competitor data provided.", normal_style))
    story.append(Spacer(1, 12))

    # ─── TenderAI (NEW - Detailed) ──────────────────────────
    story.append(Paragraph("📐 TenderAI", section_style))

    # Calculate PPR metrics using shared logic
    from modules.ppr_calculations import calculate_ppr_metrics
    ppr_metrics = calculate_ppr_metrics(est, comp_bids, nppi)

    # Add detailed calculation table
    calc_table = _create_ppr_calculation_table(est, nppi, slt, bid, comp_bids, ppr_metrics)
    story.append(calc_table)
    story.append(Spacer(1, 12))

    # Add Bid vs SLT Gauge Chart
    gauge_chart = _create_ppr_gauge_chart(est, bid, slt)
    if gauge_chart:
        story.append(Paragraph("<b>Figure 6:</b> PPR 2025 Compliance Gauge", 
                            ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
        story.append(ReportLabImage(gauge_chart, width=5*inch, height=2.5*inch))
        story.append(Spacer(1, 12))

    # Add horizontal bar comparison
    comparison_chart = _create_bid_vs_slt_chart(est, bid, slt, nppi, comparison)
    if comparison_chart:
        story.append(Paragraph("<b>Figure 7:</b> Bid vs SLT Threshold Analysis", 
                            ParagraphStyle('FigCaption', parent=normal_style, fontSize=9, textColor=colors.grey)))
        story.append(ReportLabImage(comparison_chart, width=6*inch, height=3.5*inch))
        story.append(Spacer(1, 12))

    # ─── PPR 2025 COMPLIANCE CHECK ───────────────────────────────────────────
    story.append(Paragraph("📜 PPR 2025 Compliance Check", section_style))
    is_compliant = bid >= slt
    status_color = colors.green if is_compliant else colors.red
    status_text = "✅ COMPLIANT" if is_compliant else "⚠️ SLT RISK"
    
    ppr_data = [
        ["Metric", "Value", "Status"],
        ["SLT Threshold", f"BDT {slt:,.3f}", "Reference"],  # ✅ 3 decimals
        ["Recommended Bid", f"BDT {bid:,.3f}", status_text],  # ✅ 3 decimals
        ["NPPI Factor", f"{nppi:.3f}", "Applied"],
        ["Bid Ratio", f"{bid/est*100:.1f}%" if est > 0 else "N/A", "Of Estimate"],
        ["Win Probability", f"{win_prob*100:.0f}%", "Statistical"]
    ]

    ppr_table = Table(ppr_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    ppr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dcfce7')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (2,2), (2,2), status_color),
        ('BACKGROUND', (2,2), (2,2), colors.HexColor('#dcfce7') if is_compliant else '#fee2e2'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5)
    ]))
    story.append(ppr_table)
    story.append(Spacer(1, 12))

    # ─── FINANCIAL PROJECTIONS ───────────────────────────────────────────────
    story.append(Paragraph("💰 Financial Projections", section_style))
    cost = est * 0.85
    profit = bid - cost
    exp_val = profit * win_prob
    fin_data = [
        ["Metric", "Value", "Interpretation"],
        ["Estimated Cost", f"BDT {cost:,.3f}", "85% of official estimate"],  # ✅ 3 decimals
        ["Expected Profit", f"BDT {profit:,.3f}", "If bid wins"],  # ✅ 3 decimals
        ["Expected Value", f"BDT {exp_val:,.3f}", "Profit × Win Probability"]  # ✅ 3 decimals
    ]

    fin_table = Table(fin_data, colWidths=[1.5*inch, 1.5*inch, 2*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fef3c7')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5)
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 16))

    # ─── FOOTER ──────────────────────────────────────────────────────────────
    disclaimer = Paragraph(
        "<b>Disclaimer:</b> This AI-generated analysis complies with Bangladesh PPR 2025 guidelines. Final bidding decisions should consider project-specific risks, internal cost structures, and strategic objectives. NPPI factor derived from 28-day market averages.",
        ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=12)
    )
    story.append(disclaimer)
    if user_info:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Prepared for: {safe_str(user_info.get('full_name'))} | {safe_str(user_info.get('company_name'))}",
                               ParagraphStyle('Foot', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_enhanced_analysis_report(analysis_data: dict, user_info: dict, include_charts: bool = True) -> io.BytesIO:
    """
    Enhanced PDF with safe fallbacks for missing/None values.
    Delegates to generate_babui_detailed_report for consistency.
    """
    # Transform analysis_data to match report_data format
    report_data = {
        'id': analysis_data.get('id'),
        'tender_id': analysis_data.get('tender_id'),
        'tender_title': analysis_data.get('tender_title'),
        'procuring_entity': analysis_data.get('procuring_entity'),
        'official_estimate': analysis_data.get('official_estimate'),
        'procurement_type': analysis_data.get('procurement_type'),
        'submission_deadline': analysis_data.get('submission_deadline'),
        'division': analysis_data.get('division'),
        'district': analysis_data.get('district'),
        'risk_tolerance': analysis_data.get('risk_tolerance'),
        'risk_level': analysis_data.get('risk_level'),
        'recommended_bid': analysis_data.get('recommended_bid'),
        'slt_threshold': analysis_data.get('slt_threshold'),
        'nppi_factor': analysis_data.get('nppi_factor'),
        'success_probability': analysis_data.get('success_probability'),
        'comparison': analysis_data.get('comparison'),
        'competitor_bids': analysis_data.get('competitor_bids'),
        'competitor_count': len(analysis_data.get('competitor_bids', [])),
        'bid_source': analysis_data.get('bid_source', 'Auto-Generated')
    }
    
    return generate_babui_detailed_report(report_data, user_info, include_charts)


def generate_analysis_report(analysis_data: dict, tender_info: dict, user_info: dict = None) -> io.BytesIO:
    """
    Legacy function - maintains backward compatibility.
    """
    # Merge analysis_data and tender_info
    merged_data = {**tender_info, **analysis_data}
    return generate_babui_detailed_report(merged_data, user_info, include_charts=False)

def _create_bid_vs_slt_chart(est: float, recommended_bid: float, slt: float, nppi: float, comparison: dict = None) -> io.BytesIO:
    """
    Create a bar chart comparing recommended bid against SLT threshold and other metrics.
    All monetary values displayed with 3 decimal places as per PPR 2025.
    """
    if est <= 0:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Round all values to 3 decimal places (PPR 2025 compliance)
    est = round(est, 3)
    recommended_bid = round(recommended_bid, 3)
    slt = round(slt, 3)
    nppi_price = round(est * nppi, 3)
    
    # Define categories and values
    categories = ['Official\nEstimate', 'NPPI\nPrice', 'SLT\nThreshold', 'Recommended\nBid']
    values = [est, nppi_price, slt, recommended_bid]
    colors_list = ['#9ca3af', '#f59e0b', '#ef4444', '#10b981']
    
    # Create bars
    bars = ax.bar(categories, values, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1)
    
    # Add value labels on top of bars with 3 decimal places
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + (max(values) * 0.02),
               f'BDT {val:,.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add horizontal line for recommended bid reference
    ax.axhline(y=recommended_bid, color='#10b981', linestyle='--', linewidth=1.5, alpha=0.5)
    
    # Add compliance status annotation
    is_compliant = recommended_bid >= slt
    compliance_text = "✅ COMPLIANT" if is_compliant else "⚠️ BELOW SLT"
    compliance_color = '#10b981' if is_compliant else '#ef4444'
    
    # Calculate compliance percentage with 1 decimal
    compliance_percent = (recommended_bid / slt * 100) if slt > 0 else 0
    compliance_percent = round(compliance_percent, 1)
    
    ax.text(0.5, -0.15, f'Compliance Status: {compliance_text} ({compliance_percent:.1f}% of SLT)', 
            transform=ax.transAxes, ha='center', fontsize=11, 
            fontweight='bold', color=compliance_color)
    
    ax.set_ylabel('Amount (BDT)', fontsize=11, fontweight='bold')
    ax.set_title('Bid Compliance Analysis: Recommended Bid vs SLT Threshold\n(PPR 2025 - Values shown with 3 decimal places)', 
                fontsize=11, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Format y-axis with 3 decimal places
    from matplotlib.ticker import FuncFormatter
    def format_bdt_3dec(x, p):
        if x >= 1e7:
            return f'BDT {x/1e7:.3f}Cr'
        elif x >= 1e6:
            return f'BDT {x/1e6:.3f}M'
        elif x >= 1e3:
            return f'BDT {x/1e3:.3f}K'
        return f'BDT {x:.3f}'
    
    ax.yaxis.set_major_formatter(FuncFormatter(format_bdt_3dec))
    
    plt.tight_layout()
    return _fig_to_imagerenderer(fig)


def _create_ppr_gauge_chart(est: float, recommended_bid: float, slt: float) -> io.BytesIO:
    """
    Create a gauge chart for PPR 2025 compliance with 3 decimal precision.
    """
    if est <= 0:
        return None
    
    fig, ax = plt.subplots(figsize=(6, 3))
    
    # Round values to 3 decimal places
    est = round(est, 3)
    recommended_bid = round(recommended_bid, 3)
    slt = round(slt, 3)
    
    # Calculate compliance percentage
    compliance_pct = min(100, max(0, (recommended_bid / slt) * 100)) if slt > 0 else 0
    compliance_pct = round(compliance_pct, 1)
    
    # Create horizontal bar chart
    categories = ['SLT Threshold', 'Recommended Bid']
    values = [slt, recommended_bid]
    colors_list = ['#ef4444', '#10b981']
    
    bars = ax.barh(categories, values, color=colors_list, alpha=0.7)
    
    # Add value labels with 3 decimal places
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + (max(values) * 0.02), bar.get_y() + bar.get_height()/2,
               f'BDT {val:,.3f}', va='center', fontsize=9, fontweight='bold')
    
    # Add compliance annotation
    is_compliant = recommended_bid >= slt
    status_text = f"Compliance: {compliance_pct:.1f}% of SLT"
    status_color = '#10b981' if is_compliant else '#ef4444'
    
    ax.text(0.5, -0.3, status_text, transform=ax.transAxes, ha='center', 
            fontsize=11, fontweight='bold', color=status_color)
    
    ax.set_xlabel('Amount (BDT)', fontsize=10)
    ax.set_title('PPR 2025 Compliance Status\n(3 decimal places required)', fontsize=11, fontweight='bold')
    
    # Format x-axis with 3 decimal places
    from matplotlib.ticker import FuncFormatter
    def format_bdt_3dec(x, p):
        if x >= 1e6:
            return f'BDT {x/1e6:.3f}M'
        elif x >= 1e3:
            return f'BDT {x/1e3:.3f}K'
        return f'BDT {x:.3f}'
    
    ax.xaxis.set_major_formatter(FuncFormatter(format_bdt_3dec))
    
    plt.tight_layout()
    return _fig_to_imagerenderer(fig)


def _create_ppr_calculation_table(est: float, nppi: float, slt: float, recommended_bid: float, 
                                    competitor_bids: list = None, ppr_metrics: dict = None) -> Table:
    """
    Create detailed TenderAI table with 3 decimal precision.
    """
    from reportlab.platypus import Table, TableStyle
    
    # Round all values to 3 decimal places
    est = round(est, 3)
    nppi = round(nppi, 3)
    slt = round(slt, 3)
    recommended_bid = round(recommended_bid, 3)
    
    if ppr_metrics:
        avg_comp = round(ppr_metrics.get('avg_competitor', 0), 3)
        weighted_avg = round(ppr_metrics.get('weighted_average', 0), 3)
        weighted_std = round(ppr_metrics.get('weighted_std_dev', 0), 3)
        nppi_price = round(ppr_metrics.get('nppi_price', est * nppi), 3)
    else:
        comp_values = [c.get('bid', 0) for c in (competitor_bids or []) if c.get('bid', 0) > 0]
        avg_comp = round(sum(comp_values) / len(comp_values), 3) if comp_values else 0
        nppi_price = round(est * nppi, 3)
        weighted_avg = round((0.5 * avg_comp) + (0.2 * est) + (0.3 * nppi_price), 3) if avg_comp > 0 else round(est * 0.85, 3)
        weighted_std = round(np.std(comp_values), 3) if len(comp_values) > 1 else round(est * 0.05, 3)
    
    # Build calculation steps with 3 decimal places
    calc_data = [
        ["Step", "Formula", "Value", "Result (BDT)"],
        ["1. Official Estimate", "From tender document", f"{est:,.3f}", "Base Value"],
        ["2. NPPI Factor", "28-day market average", f"{nppi:.3f}", "Index Factor"],
        ["3. NPPI Price", "Estimate × NPPI", f"{est:,.3f} × {nppi:.3f}", f"{nppi_price:,.3f}"],
        ["4. Avg Competitor", "Σ(Comp Bids) / N", f"({len(competitor_bids or [])} bids)", f"{avg_comp:,.3f}" if avg_comp > 0 else "N/A"],
        ["5. Weighted Avg (X̄)", "0.5(Avg Comp) + 0.2(Est) + 0.3(NPPI)", f"0.5×{avg_comp:,.3f} + 0.2×{est:,.3f} + 0.3×{nppi_price:,.3f}", f"{weighted_avg:,.3f}"],
        ["6. Std Deviation (Sd)", "Statistical dispersion", f"σ = {weighted_std:.3f}", f"{weighted_std:,.3f}"],
        ["7. SLT Threshold", "X̄ - Sd", f"{weighted_avg:,.3f} - {weighted_std:,.3f}", f"{slt:,.3f}"],
        ["8. Recommended Bid", "Optimized by AI", "Based on win probability", f"{recommended_bid:,.3f}"],
        ["9. Compliance", "Bid ≥ SLT?", f"{recommended_bid:,.3f} ≥ {slt:,.3f}", "✅ PASS" if recommended_bid >= slt else "❌ FAIL"],
    ]
    
    # Create table with styling
    table = Table(calc_data, colWidths=[0.7*inch, 2*inch, 1.5*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,1), (-1,-2), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#dcfce7') if recommended_bid >= slt else colors.HexColor('#fee2e2')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    return table
def _generate_and_download_pdf(analysis_id: int, analysis_record: dict) -> None:
    """Helper with bulletproof logging and fallbacks"""
    debug_print(f"🚀 PDF HELPER START | id={analysis_id}, record_type={type(analysis_record)}")
    
    with st.spinner("🔄 Generating PDF report..."):
        try:
            from modules.pdf_generator import generate_enhanced_analysis_report
            
            user_info = {
                'full_name': st.session_state.get('full_name', 'N/A'),
                'company_name': st.session_state.get('company_name', 'N/A'),
                'role': st.session_state.get('user_role', 'N/A'),
                'email': st.session_state.get('user_email', 'N/A'),
            }
            debug_print(f"👤 User Info: {user_info}")

            # Fetch from DB if ID provided
            if analysis_id:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tender_analyses WHERE id = ?', (analysis_id,))
                saved = cursor.fetchone()
                conn.close()
                
                if saved and cursor.description:
                    cols = [d[0] for d in cursor.description]
                    db_record = dict(zip(cols, saved))
                    report_data = {**analysis_record, **db_record}
                else:
                    report_data = analysis_record
            else:
                report_data = analysis_record
            
            # Safe type conversions
            est = float(report_data.get('official_estimate') or 1)
            bid = float(report_data.get('recommended_bid') or 0)
            slt = float(report_data.get('slt_threshold') or (est * 0.80))
            nppi = float(report_data.get('nppi_factor') or 0.92)
            win_prob = float(report_data.get('success_probability') or 0.6)
            
            report_data.update({
                'official_estimate': est,
                'recommended_bid': bid,
                'slt_threshold': slt,
                'nppi_factor': nppi,
                'success_probability': win_prob
            })
            debug_print(f"💰 Converted values: est={est}, bid={bid}, slt={slt}")
            
            # Generate PDF
            pdf_buffer = generate_enhanced_analysis_report(report_data, user_info, include_charts=True)
            
            # Validate buffer
            if not pdf_buffer or pdf_buffer.getbuffer().nbytes == 0:
                st.error("❌ PDF generation returned empty buffer")
                return
            
            debug_print(f"✅ PDF generated | size={pdf_buffer.getbuffer().nbytes} bytes")
            
            # Store in session state
            safe_tid = str(report_data.get('tender_id', 'report')).replace('/', '_').replace('\\', '_').replace(' ', '_')
            filename = f"Enhanced_Analysis_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            
            st.session_state._pdf_buffer = pdf_buffer
            st.session_state._pdf_filename = filename
            
            st.success("✅ PDF generated! Scroll down to download.")
            
        except ImportError as e:
            st.warning(f"⚠️ PDF module not available: {e}")
        except Exception as e:
            st.error(f"❌ PDF error: {str(e)}")
            if DEBUG_MODE:
                with st.expander("🐛 PDF Helper Traceback"):
                    st.code(traceback.format_exc(), language="python")