# modules/html_report_generator.py - COMPLETE FIXED VERSION

"""
HTML Report Generator for Bid Analysis Modules
Generates professional HTML reports that can be printed to PDF
"""

import io
from datetime import datetime
from typing import Dict, Any, Optional
import streamlit as st


def generate_bid_html_report(analysis_data: Dict[str, Any], user_info: Dict[str, Any], tier: str = "advanced") -> str:
    """Generate HTML report for bid analysis results."""
    
    # Extract common data
    tender_id = analysis_data.get('tender_id', 'N/A')
    tender_title = analysis_data.get('tender_title', 'N/A')
    official_estimate = analysis_data.get('official_estimate', 0)
    recommended_bid = analysis_data.get('recommended_bid', 0)
    win_probability = analysis_data.get('win_probability', 0) * 100
    risk_level = analysis_data.get('risk_level', 'MEDIUM')
    expected_profit = analysis_data.get('expected_profit', 0)
    expected_value = analysis_data.get('expected_value', 0)
    
    # Risk color mapping
    risk_colors = {
        'LOW': '#4caf50',
        'MEDIUM': '#ff9800', 
        'MEDIUM-HIGH': '#f44336',
        'HIGH': '#d32f2f',
        'MEDIUM-LOW': '#8bc34a'
    }
    risk_color = risk_colors.get(risk_level, '#2196f3')
    
    # Tier-specific data
    if tier == "competitive":
        recommendations = analysis_data.get('recommendations', {})
        unified = analysis_data.get('unified', {})
        scenario_count = analysis_data.get('scenario_count', 0)
        competitor_range = analysis_data.get('competitor_range', '5-19')
        nppi_range = analysis_data.get('nppi_range', '0.920-0.942')
        risk_tolerance = analysis_data.get('risk_tolerance', 'moderate')
        boq_cost = analysis_data.get('boq_cost', 0)
    else:
        nppi_factor = analysis_data.get('nppi_factor', 0.920)
        slt_threshold = analysis_data.get('slt_threshold', official_estimate * 0.85)
        competitor_count = analysis_data.get('competitor_count', 0)
        cost_profile = analysis_data.get('cost_profile', 'competitive')
        confidence_score = analysis_data.get('confidence_score', 0) * 100
        boq_cost = analysis_data.get('boq_cost', 0)
    
    # ✅ Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bid Analysis Report - {tender_id}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .header .tier-badge {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 4px 16px;
                border-radius: 20px;
                margin-top: 10px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .header p {{
                margin: 10px 0 0;
                opacity: 0.9;
            }}
            .content {{
                padding: 30px;
            }}
            .section {{
                margin-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
                margin-bottom: 0;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: bold;
                color: #1e3c72;
                margin-bottom: 15px;
                padding-bottom: 5px;
                border-bottom: 2px solid #667eea;
                display: inline-block;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-top: 15px;
            }}
            .info-grid-3 {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-top: 15px;
            }}
            .info-item {{
                background: #f8f9fa;
                padding: 12px 15px;
                border-radius: 6px;
            }}
            .info-label {{
                font-weight: bold;
                color: #555;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }}
            .info-value {{
                font-size: 16px;
                font-weight: 500;
                color: #333;
            }}
            .metric-box {{
                background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 15px 0;
                border: 1px solid #667eea30;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
                color: #2a5298;
            }}
            .metric-label {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            .metric-sub {{
                font-size: 13px;
                color: #888;
                margin-top: 2px;
            }}
            .risk-badge {{
                display: inline-block;
                padding: 4px 16px;
                background: {risk_color};
                color: white;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 11px;
                color: #999;
                border-top: 1px solid #e0e0e0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px 12px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
                color: #333;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .status-compliant {{ color: #28a745; font-weight: bold; }}
            .status-non-compliant {{ color: #dc3545; font-weight: bold; }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .container {{ box-shadow: none; border-radius: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 BID ANALYSIS REPORT</h1>
                <div class="tier-badge">{tier.upper()} ANALYSIS</div>
                <p>Generated on {datetime.now().strftime('%d %B %Y at %H:%M:%S')}</p>
            </div>
            
            <div class="content">
                <!-- Report Metadata -->
                <div class="section">
                    <div class="section-title">📋 Report Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Report ID</div>
                            <div class="info-value">BAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Generated By</div>
                            <div class="info-value">{user_info.get('full_name', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Company</div>
                            <div class="info-value">{user_info.get('company_name', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Analysis Tier</div>
                            <div class="info-value">{tier.upper()}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Tender Information -->
                <div class="section">
                    <div class="section-title">📌 Tender Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Tender ID</div>
                            <div class="info-value">{tender_id}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Tender Title</div>
                            <div class="info-value">{tender_title[:80]}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Official Estimate (OCE)</div>
                            <div class="info-value">BDT {official_estimate:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Procurement Type</div>
                            <div class="info-value">{analysis_data.get('procurement_type', 'N/A').upper()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">BOQ Cost</div>
                            <div class="info-value">BDT {boq_cost:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Analysis Date</div>
                            <div class="info-value">{analysis_data.get('analysis_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</div>
                        </div>
                    </div>
                </div>
    """
    
    # ===== TIER-SPECIFIC SECTIONS =====
    
    if tier == "quick":
        html += f"""
                <!-- Quick Bid Results -->
                <div class="section">
                    <div class="section-title">⚡ Quick Bid Recommendation</div>
                    <div class="metric-box">
                        <div class="metric-value">BDT {recommended_bid:,.3f}</div>
                        <div class="metric-label">Recommended Bid</div>
                        <div class="metric-sub">{recommended_bid/official_estimate*100:.1f}% of OCE</div>
                    </div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Win Probability</div>
                            <div class="info-value">{win_probability:.0f}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Risk Level</div>
                            <div class="info-value"><span class="risk-badge">{risk_level}</span></div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Profit</div>
                            <div class="info-value">BDT {expected_profit:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Strategy</div>
                            <div class="info-value">{analysis_data.get('strategy', 'Moderate').capitalize()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">NPPI Factor</div>
                            <div class="info-value">{analysis_data.get('nppi_factor', 0.920):.4f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">SLT Threshold (Simplified)</div>
                            <div class="info-value">BDT {analysis_data.get('slt_threshold', official_estimate * 0.80):,.3f}</div>
                        </div>
                    </div>
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <b>💡 Quick Estimate:</b> Heuristic recommendation based on OCE with optional NPPI. 
                        Upgrade to Advanced for PPR 2025 compliance with full SLT analysis.
                    </div>
                </div>
        """
    
    elif tier == "advanced":
        html += f"""
                <!-- Advanced Bid Results -->
                <div class="section">
                    <div class="section-title">📈 Advanced Bid Recommendation</div>
                    <div class="metric-box">
                        <div class="metric-value">BDT {recommended_bid:,.3f}</div>
                        <div class="metric-label">Optimal Bid</div>
                        <div class="metric-sub">{recommended_bid/official_estimate*100:.1f}% of OCE</div>
                    </div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Win Probability</div>
                            <div class="info-value">{win_probability:.0f}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Risk Level</div>
                            <div class="info-value"><span class="risk-badge">{risk_level}</span></div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Profit</div>
                            <div class="info-value">BDT {expected_profit:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Value</div>
                            <div class="info-value">BDT {expected_value:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Cost Profile</div>
                            <div class="info-value">{cost_profile.capitalize()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Confidence Score</div>
                            <div class="info-value">{confidence_score:.0f}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">BOQ Cost</div>
                            <div class="info-value">BDT {boq_cost:,.3f}</div>
                        </div>
                    </div>
                </div>
                
                <!-- PPR 2025 Metrics -->
                <div class="section">
                    <div class="section-title">📐 PPR 2025 Compliance Metrics</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">NPPI Factor</div>
                            <div class="info-value">{nppi_factor:.4f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">SLT Threshold</div>
                            <div class="info-value">BDT {slt_threshold:,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Competitors Analyzed</div>
                            <div class="info-value">{competitor_count}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Bid vs SLT</div>
                            <div class="info-value">
                                <span class="{'status-compliant' if recommended_bid >= slt_threshold else 'status-non-compliant'}">
                                    {recommended_bid/slt_threshold*100:.1f}% of SLT
                                </span>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Weighted Average (WA)</div>
                            <div class="info-value">BDT {analysis_data.get('weighted_average', 0):,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Weighted Std Dev (WSD)</div>
                            <div class="info-value">BDT {analysis_data.get('weighted_std_dev', 0):,.3f}</div>
                        </div>
                    </div>
                    <div style="background: {'#e8f5e9' if recommended_bid >= slt_threshold else '#ffebee'}; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <b>PPR Compliance Status:</b> 
                        {'✅ Compliant' if recommended_bid >= slt_threshold else '❌ Non-Compliant'}
                        <br>
                        <b>Recommended Action:</b> 
                        {'Bid is above SLT threshold. Proceed with submission.' if recommended_bid >= slt_threshold else '⚠️ Bid is below SLT threshold. Consider increasing bid or providing justification.'}
                    </div>
                </div>
        """
    
    else:  # competitive
        # Build profile rows
        profile_rows = ""
        for profile, data in recommendations.items():
            bid = data.get('bid', 0)
            win = data.get('win_prob', 0) * 100
            profit = data.get('profit', 0)
            risk = data.get('risk_level', 'MEDIUM')
            risk_color = risk_colors.get(risk, '#2196f3')
            profile_rows += f"""
                            <tr>
                                <td><strong>{profile.upper()}</strong></td>
                                <td>BDT {bid:,.3f}</td>
                                <td>{win:.0f}%</td>
                                <td>BDT {profit:,.3f}</td>
                                <td><span class="risk-badge" style="background: {risk_color}; font-size: 10px;">{risk}</span></td>
                            </tr>
            """
        
        html += f"""
                <!-- Competitive Intelligence Results -->
                <div class="section">
                    <div class="section-title">🧠 Competitive Intelligence Results</div>
                    <div class="metric-box">
                        <div class="metric-value">BDT {recommended_bid:,.3f}</div>
                        <div class="metric-label">Unified Recommended Bid</div>
                        <div class="metric-sub">{recommended_bid/official_estimate*100:.1f}% of OCE | Profile: {unified.get('profile', 'N/A').upper()}</div>
                    </div>
                    <div class="info-grid-3">
                        <div class="info-item">
                            <div class="info-label">Risk Tolerance</div>
                            <div class="info-value">{risk_tolerance.capitalize()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Scenarios</div>
                            <div class="info-value">{scenario_count}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Competitor Range</div>
                            <div class="info-value">{competitor_range}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">NPPI Range</div>
                            <div class="info-value">{nppi_range}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">BOQ Cost</div>
                            <div class="info-value">BDT {boq_cost:,.3f}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Three Cost Profiles -->
                <div class="section">
                    <div class="section-title">💰 Three Cost Profile Recommendations</div>
                    <table>
                        <thead>
                            <tr>
                                <th>Profile</th>
                                <th>Bid Amount</th>
                                <th>Win Probability</th>
                                <th>Expected Profit</th>
                                <th>Risk Level</th>
                            </tr>
                        </thead>
                        <tbody>
                            {profile_rows}
                        </tbody>
                    </table>
                    <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <b>🏆 Unified Recommendation:</b> <strong>{unified.get('profile', 'N/A').upper()}</strong> profile<br>
                        <b>Expected Value:</b> BDT {unified.get('ev', 0):,.3f}
                    </div>
                </div>
        """
    
    html += f"""
            </div>
            
            <div class="footer">
                Generated by TenderAI Bid Analysis System<br>
                © {datetime.now().year} TenderAI. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def generate_ai_advisor_report(ai_data: Dict[str, Any], user_info: Dict[str, Any]) -> str:
    """Generate AI Bid Advisor executive summary report."""
    
    summary = ai_data.get('summary', 'No summary available.')
    strategy = ai_data.get('strategy', 'No strategy recommendation.')
    metrics = ai_data.get('metrics', {})
    risk = ai_data.get('risk', 'MEDIUM')
    analysis_type = ai_data.get('analysis_type', 'Advanced Bid Analysis')
    
    risk_colors = {
        'LOW': '#4caf50',
        'MEDIUM': '#ff9800', 
        'MEDIUM-HIGH': '#f44336',
        'HIGH': '#d32f2f',
        'MEDIUM-LOW': '#8bc34a'
    }
    risk_color = risk_colors.get(risk, '#2196f3')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI Bid Advisor Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .header .tier-badge {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 4px 16px;
                border-radius: 20px;
                margin-top: 10px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .content {{
                padding: 30px;
            }}
            .section {{
                margin-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 20px;
            }}
            .section:last-child {{
                border-bottom: none;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: bold;
                color: #1e3c72;
                margin-bottom: 15px;
                padding-bottom: 5px;
                border-bottom: 2px solid #667eea;
                display: inline-block;
            }}
            .executive-summary {{
                background: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                font-size: 16px;
                line-height: 1.6;
                border-left: 4px solid #1e3c72;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin-top: 15px;
            }}
            .info-item {{
                background: #f8f9fa;
                padding: 12px 15px;
                border-radius: 6px;
            }}
            .info-label {{
                font-weight: bold;
                color: #555;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }}
            .info-value {{
                font-size: 16px;
                font-weight: 500;
                color: #333;
            }}
            .risk-badge {{
                display: inline-block;
                padding: 4px 16px;
                background: {risk_color};
                color: white;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .strategy-box {{
                background: #f0f4f8;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                margin-top: 15px;
            }}
            .next-steps {{
                background: #e8f5e9;
                padding: 15px 20px;
                border-radius: 8px;
                margin-top: 15px;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 11px;
                color: #999;
                border-top: 1px solid #e0e0e0;
            }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .container {{ box-shadow: none; border-radius: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI BID ADVISOR</h1>
                <div class="tier-badge">EXECUTIVE SUMMARY</div>
                <p>Generated on {datetime.now().strftime('%d %B %Y at %H:%M:%S')}</p>
            </div>
            
            <div class="content">
                <!-- Report Info -->
                <div class="section">
                    <div class="section-title">📋 Report Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Report ID</div>
                            <div class="info-value">AI-{datetime.now().strftime('%Y%m%d-%H%M%S')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Generated By</div>
                            <div class="info-value">{user_info.get('full_name', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Company</div>
                            <div class="info-value">{user_info.get('company_name', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Analysis Type</div>
                            <div class="info-value">{analysis_type}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Executive Summary -->
                <div class="section">
                    <div class="section-title">📌 Executive Summary</div>
                    <div class="executive-summary">
                        {summary}
                    </div>
                </div>
                
                <!-- Key Metrics -->
                <div class="section">
                    <div class="section-title">📊 Key Metrics</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Recommended Bid</div>
                            <div class="info-value">BDT {metrics.get('bid', 0):,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Win Probability</div>
                            <div class="info-value">{metrics.get('win_prob', 0)*100:.0f}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Profit</div>
                            <div class="info-value">BDT {metrics.get('profit', 0):,.3f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Risk Level</div>
                            <div class="info-value"><span class="risk-badge">{risk}</span></div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Strategy</div>
                            <div class="info-value">{metrics.get('strategy', 'Balanced')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Decision Confidence</div>
                            <div class="info-value">{metrics.get('confidence', 85)}%</div>
                        </div>
                    </div>
                </div>
                
                <!-- Recommended Strategy -->
                <div class="section">
                    <div class="section-title">💡 Recommended Strategy</div>
                    <div class="strategy-box">
                        {strategy}
                    </div>
                </div>
                
                <!-- Key Risks -->
                <div class="section">
                    <div class="section-title">⚠️ Key Risks</div>
                    <ul style="padding-left: 20px; line-height: 1.8;">
                        <li><strong>Risk Level:</strong> {risk}</li>
                        <li>Competitor density may force lower bids</li>
                        <li>Cost estimate variations can impact profitability</li>
                        <li>Market conditions may change before submission</li>
                    </ul>
                    <div style="background: #fff3e0; padding: 12px 15px; border-radius: 6px; margin-top: 10px; border-left: 3px solid #ff9800;">
                        <b>Risk Mitigation:</b> Review cost estimates, monitor competitor activity, maintain flexibility in pricing strategy.
                    </div>
                </div>
                
                <!-- Next Steps -->
                <div class="section">
                    <div class="section-title">📌 Next Steps</div>
                    <div class="next-steps">
                        <ol style="margin: 0; padding-left: 20px; line-height: 2;">
                            <li>Review detailed scenario analysis in the full report</li>
                            <li>Adjust bid if risk tolerance changes</li>
                            <li>Prepare justification documentation for internal approval</li>
                            <li>Monitor competitor activity before final submission</li>
                            <li>Set up post-award evaluation tracking</li>
                        </ol>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                AI Bid Advisor powered by TenderAI<br>
                © {datetime.now().year} TenderAI. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def generate_analysis_report(analysis_data: Dict[str, Any], user_info: Dict[str, Any], tier: str = "advanced") -> io.BytesIO:
    """
    Generate HTML report and return as downloadable buffer.
    
    Args:
        analysis_data: Dictionary containing analysis results
        user_info: Dictionary with user/company info
        tier: 'quick', 'advanced', 'competitive', or 'ai'
    
    Returns:
        BytesIO buffer containing HTML report
    """
    
    if tier == "ai":
        html_content = generate_ai_advisor_report(analysis_data, user_info)
    else:
        html_content = generate_bid_html_report(analysis_data, user_info, tier)
    
    buffer = io.BytesIO()
    buffer.write(html_content.encode('utf-8'))
    buffer.seek(0)
    
    return buffer


def render_html_report_download_button(analysis_data: Dict[str, Any], tier: str = "advanced", button_label: str = "📄 Generate HTML Report"):
    """
    Render a download button for HTML report in Streamlit.
    """
    user_info = {
        'full_name': st.session_state.get('full_name', 'User'),
        'company_name': st.session_state.get('company_name', 'N/A')
    }
    
    if st.button(button_label, use_container_width=True):
        report_buffer = generate_analysis_report(analysis_data, user_info, tier)
        filename = f"{tier}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        st.download_button(
            "📥 Download HTML Report",
            report_buffer,
            filename,
            "text/html",
            use_container_width=True
        )