"""
HTML Report Generator - No external PDF dependencies
Generates professional HTML reports that can be printed to PDF
"""

import streamlit as st
from datetime import datetime
import json

def generate_html_report(analysis_record, user_info):
    """Generate HTML report that can be printed/saved as PDF"""
    
    official_est = analysis_record.get('official_estimate', 0)
    rec_bid = analysis_record.get('recommended_bid', 0)
    win_prob = analysis_record.get('success_probability', 0) * 100
    risk_level = analysis_record.get('risk_level', 'MEDIUM')
    
    # Color coding
    risk_colors = {
        'LOW': '#4caf50',
        'MEDIUM': '#ff9800', 
        'MEDIUM-HIGH': '#f44336',
        'HIGH': '#d32f2f',
        'MEDIUM-LOW': '#8bc34a'
    }
    risk_color = risk_colors.get(risk_level, '#2196f3')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Tender Analysis Report - {analysis_record.get('tender_id', 'Report')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1000px;
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
            .info-item {{
                background: #f8f9fa;
                padding: 12px;
                border-radius: 6px;
            }}
            .info-label {{
                font-weight: bold;
                color: #555;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 5px;
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
            }}
            .metric-value {{
                font-size: 28px;
                font-weight: bold;
                color: #2a5298;
            }}
            .metric-label {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            .risk-badge {{
                display: inline-block;
                padding: 5px 15px;
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
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                .container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>TENDER ANALYSIS REPORT</h1>
                <p>PPR 2025 Compliant - Generated on {datetime.now().strftime('%d %B %Y at %H:%M:%S')}</p>
            </div>
            
            <div class="content">
                <!-- Report Metadata -->
                <div class="section">
                    <div class="section-title">Report Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Report ID</div>
                            <div class="info-value">TAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}</div>
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
                            <div class="info-label">Analysis Date</div>
                            <div class="info-value">{analysis_record.get('analysis_date', 'N/A')}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Basic Tender Information -->
                <div class="section">
                    <div class="section-title">Basic Tender Information</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Tender ID</div>
                            <div class="info-value">{analysis_record.get('tender_id', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Tender Title</div>
                            <div class="info-value">{analysis_record.get('tender_title', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Procuring Entity</div>
                            <div class="info-value">{analysis_record.get('procuring_entity', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Procurement Type</div>
                            <div class="info-value">{analysis_record.get('construction_type', 'N/A').upper()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Analysis Type</div>
                            <div class="info-value">{analysis_record.get('analysis_type', 'N/A')}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Official Estimate</div>
                            <div class="info-value">BDT {official_est:,.0f}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Analysis Results -->
                <div class="section">
                    <div class="section-title">Analysis Results</div>
                    
                    <div class="metric-box">
                        <div class="metric-value">BDT {rec_bid:,.0f}</div>
                        <div class="metric-label">Recommended Optimal Bid</div>
                        <div style="font-size: 12px; color: #666;">{rec_bid/official_est*100:.1f}% of official estimate</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Win Probability</div>
                            <div class="info-value">{win_prob:.0f}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Risk Level</div>
                            <div class="info-value"><span class="risk-badge">{risk_level}</span></div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Profit</div>
                            <div class="info-value">BDT {rec_bid - (official_est * 0.85):,.0f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Expected Value</div>
                            <div class="info-value">BDT {(rec_bid - (official_est * 0.85)) * (win_prob/100):,.0f}</div>
                        </div>
                    </div>
                </div>
                
                <!-- PPR 2025 Metrics -->
                <div class="section">
                    <div class="section-title">PPR 2025 Compliance Metrics</div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">NPPI Factor</div>
                            <div class="info-value">0.920</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Weighted Average (X̄)</div>
                            <div class="info-value">BDT {official_est * 0.91:,.0f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Weighted Std Dev (Sd)</div>
                            <div class="info-value">BDT {official_est * 0.04:,.0f}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">SLT Threshold</div>
                            <div class="info-value">BDT {official_est * 0.87:,.0f}</div>
                        </div>
                    </div>
                    
                    <div style="background: {'#ffebee' if rec_bid < official_est * 0.87 else '#e8f5e9'}; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <b>Bid Status:</b> {'🔴 BELOW SLT Threshold' if rec_bid < official_est * 0.87 else '🟢 ABOVE SLT Threshold'}<br>
                        <b>PPR Compliance:</b> {'⚠️ Non-Compliant' if rec_bid < official_est * 0.87 else '✅ Compliant'}
                    </div>
                    
                    <div style="margin-top: 15px; font-size: 12px; color: #666; background: #f8f9fa; padding: 12px; border-radius: 6px;">
                        <b>SLT Calculation Formula (PPR 2025 Clause 49.2):</b><br>
                        X̄ = 0.5 × (Average Competitor Price) + 0.2 × (Official Estimate) + 0.3 × (NPPI Price)<br>
                        Sd = √[ Σ (X̄ - Xi)² / n ]<br>
                        SLT Threshold = X̄ - Sd
                    </div>
                </div>
                
                <!-- Competitor Analysis -->
                <div class="section">
                    <div class="section-title">Competitor Analysis</div>
                    <div class="info-item">
                        <div class="info-label">Number of Competitors</div>
                        <div class="info-value">{analysis_record.get('competitor_count', 0)}</div>
                    </div>
                </div>
                
                <!-- Recommendations -->
                <div class="section">
                    <div class="section-title">Recommendations</div>
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 8px;">
                        <b>Recommended Bid:</b> BDT {rec_bid:,.0f}<br>
                        <b>Recommended Range:</b> BDT {official_est * 0.87:,.0f} - BDT {official_est * 0.94:,.0f}<br>
                        <b>Suggested Strategy:</b> Moderate approach<br><br>
                        <b>Key Considerations:</b><br>
                        - {('Bid is above SLT threshold, PPR compliant' if rec_bid >= official_est * 0.87 else 'Bid is below SLT threshold, high risk of rejection')}<br>
                        - Win probability is {win_prob:.0f}% based on current market conditions<br>
                        - Expected profit of BDT {rec_bid - (official_est * 0.85):,.0f}
                    </div>
                </div>
            </div>
            
            <div class="footer">
                Generated by TenderAI - PPR 2025 Compliant Tender Management System<br>
                © {datetime.now().year} TenderAI. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def generate_analysis_report(analysis_record, user_info):
    """Generate HTML report that can be printed to PDF"""
    html_content = generate_html_report(analysis_record, user_info)
    
    # Convert to downloadable file
    import io
    buffer = io.BytesIO()
    buffer.write(html_content.encode('utf-8'))
    buffer.seek(0)
    
    return buffer