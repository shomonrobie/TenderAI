"""
TenderAI HTML Report Generator Module
PPR 2025 Compliant - Professional HTML Report Generation
"""

import base64
from datetime import datetime
import streamlit as st
import pandas as pd


class HTMLReportGenerator:
    """Generate professional HTML reports for bid optimization results."""
    
    def __init__(self, analysis_data):
        """Initialize with analysis data."""
        self.data = analysis_data
        self.timestamp = datetime.now()
    
    def generate_html(self):
        """Generate complete HTML report."""
        
        # Extract data with defaults
        data = self.data
        official_estimate = data.get('official_estimate', 0)
        recommended_bid = data.get('recommended_bid', official_estimate * 0.92)
        bid_ratio = recommended_bid / official_estimate if official_estimate > 0 else 0
        win_probability = data.get('win_probability', 0.65)
        slt_threshold = data.get('slt_threshold', official_estimate * 0.85)
        competitor_count = data.get('competitor_count', 0)
        risk_level = data.get('risk_level', 'MEDIUM')
        confidence_score = data.get('confidence_score', 0.75)
        ai_strategy = data.get('ai_strategy', 'weighted_ensemble')
        estimated_cost = data.get('estimated_cost', official_estimate * 0.85)
        expected_profit = recommended_bid - estimated_cost
        
        # NPPI information
        nppi_mode = data.get('nppi_mode', 'N/A')
        nppi_min = data.get('nppi_min', 0.920)
        nppi_max = data.get('nppi_max', 0.942)
        avg_nppi = data.get('nppi_factor', (nppi_min + nppi_max) / 2)
        
        # Get scenario data
        scenarios = data.get('scenarios', [])
        scenarios_full = data.get('scenarios_full', [])
        tier_comparison = data.get('tier_comparison', {})
        competitor_bids = data.get('competitor_bids', [])
        
        # Strategy name mapping
        strategy_names = {
            'weighted_ensemble': 'Weighted Ensemble (Balanced)',
            'conservative': 'Conservative (Highest Profit)',
            'aggressive': 'Aggressive (Highest Win Chance)',
            'statistical': 'Statistical (Mean - 0.5*Std)',
            'ml_style': 'ML-Style (Regression-based)'
        }
        strategy_display = strategy_names.get(ai_strategy, ai_strategy.replace('_', ' ').title())
        
        # Compliance check
        is_compliant = recommended_bid >= slt_threshold
        compliance_badge = '<span class="badge" style="background:#10b98120; color:#10b981;">✅ COMPLIANT</span>' if is_compliant else '<span class="badge" style="background:#ef444420; color:#ef4444;">⚠️ NON-COMPLIANT</span>'
        
        # Get user info
        user_name = st.session_state.get('full_name', 'User')
        user_role = st.session_state.get('user_role', 'user')
        company_name = st.session_state.get('company_name', 'N/A')
        
        # Generate tables
        scenario_table = self._generate_scenario_table(scenarios)
        detailed_scenarios = self._generate_detailed_scenarios(scenarios_full)
        competitor_table = self._generate_competitor_table(competitor_bids, official_estimate)
        tier_table = self._generate_tier_table(tier_comparison)
        calculation_table = self._generate_calculation_table(data, official_estimate)
        risk_assessment = self._generate_risk_assessment(risk_level, bid_ratio)
        nppi_table = self._generate_nppi_table(scenarios)
        
        bid_ratio_pct = bid_ratio * 100
        less_or_above = 100 - bid_ratio_pct

        if less_or_above > 0:
            vs_text = f'⬇️ {less_or_above:.1f}%'
            vs_color = '#10b981'  # Green
        else:
            vs_text = f'⬆️ {abs(less_or_above):.1f}%'
            vs_color = '#ef4444'  # Red

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TenderAI - Competitive Bid Simulator Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; 
        }}
        .report-container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); 
            overflow: hidden; 
        }}
        .header {{ 
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
            color: white; 
            padding: 40px 30px; 
            text-align: center;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ font-size: 14px; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ 
            font-size: 22px; 
            font-weight: bold; 
            color: #1e3a8a; 
            border-left: 5px solid #3b82f6; 
            padding-left: 15px; 
            margin-bottom: 20px;
        }}
        .info-grid {{ 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            background: #f8fafc; 
            padding: 20px; 
            border-radius: 16px; 
        }}
        .info-item {{ 
            padding: 12px; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        }}
        .info-label {{ font-size: 11px; color: #64748b; margin-bottom: 5px; }}
        .info-value {{ font-size: 16px; font-weight: bold; color: #1e293b; }}
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            margin: 20px 0; 
        }}
        .stat-card {{ 
            text-align: center; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            border-radius: 16px;
        }}
        .stat-value {{ font-size: 24px; font-weight: bold; }}
        .stat-label {{ font-size: 12px; opacity: 0.9; margin-top: 5px; }}
        .recommendation-box {{ 
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); 
            border-left: 5px solid #10b981; 
            padding: 25px; 
            border-radius: 16px; 
            margin: 20px 0; 
        }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #1e3a8a; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
        tr:hover {{ background: #f8fafc; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .footer {{ 
            background: #f1f5f9; 
            padding: 20px; 
            text-align: center; 
            font-size: 11px; 
            color: #64748b; 
        }}
        .progress-bar {{
            background: #e2e8f0;
            border-radius: 10px;
            height: 8px;
            overflow: hidden;
        }}
        .progress-fill {{
            background: #3b82f6;
            height: 100%;
            border-radius: 10px;
        }}
        .nppi-badge {{
            background: #fef3c7;
            color: #d97706;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: bold;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .stat-card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🤖 TenderAI | Competitive Bid Simulation Report</h1>
            <p>PPR 2025 Compliant Bid Optimization System</p>
            <small>Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | Report ID: {data.get('tender_id', 'N/A')}</small>
        </div>
        
        <div class="content">
            <!-- Key Metrics -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{competitor_count}</div>
                        <div class="stat-label">Competitors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{win_probability*100:.0f}%</div>
                        <div class="stat-label">Win Probability</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">BDT {recommended_bid:,.3f}</div>
                        <div class="stat-label">Recommended Bid</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: {vs_color};">{vs_text}</div>
                        <div class="stat-label">vs OCE</div>
                    </div>
                </div>

            
            <!-- Tender Information -->
            <div class="section">
                <div class="section-title">📋 Tender Information</div>
                <div class="info-grid">
                    <div class="info-item"><div class="info-label">Tender ID</div><div class="info-value">{data.get('tender_id', 'N/A')}</div></div>
                    <div class="info-item"><div class="info-label">Tender Title</div><div class="info-value">{data.get('tender_title', 'N/A')[:60]}</div></div>
                    <div class="info-item"><div class="info-label">Procuring Entity</div><div class="info-value">{data.get('procuring_entity', 'N/A')[:40]}</div></div>
                    <div class="info-item"><div class="info-label">Official Estimate</div><div class="info-value">BDT {official_estimate:,.3f}</div></div>
                    <div class="info-item"><div class="info-label">Procurement Type</div><div class="info-value">{data.get('procurement_type', 'WORKS').upper()}</div></div>
                    <div class="info-item"><div class="info-label">Location</div><div class="info-value">{data.get('division', 'N/A')} / {data.get('district', 'N/A')}</div></div>
                    <div class="info-item"><div class="info-label">Risk Tolerance</div><div class="info-value">{data.get('risk_tolerance', 'Moderate')}</div></div>
                    <div class="info-item"><div class="info-label">AI Strategy</div><div class="info-value">{strategy_display}</div></div>
                </div>
            </div>
            
            <!-- AI Recommendation -->
            <div class="section">
                <div class="section-title">🎯 AI Recommendation</div>
                <div class="recommendation-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 15px;">
                        <div>
                            <strong style="font-size: 18px;">💡 Strategic Bid Recommendation</strong><br>
                            <span style="font-size: 13px; color: #065f46;">Based on {len(scenarios)} competitor scenarios</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 22px; font-weight: bold; color: #065f46;">BDT {recommended_bid:,.3f}</div>
                            <div style="font-size: 12px;">{bid_ratio*100:.1f}% of Estimate</div>
                        </div>
                    </div>
                    <p>Optimal bid is <strong>BDT {recommended_bid:,.3f}</strong> ({bid_ratio*100:.1f}% of estimate) with <strong>{win_probability*100:.0f}% win probability</strong>, safely above SLT threshold of BDT {slt_threshold:,.3f}.</p>
                    <p style="margin-top: 10px;">Strategy: <strong>{strategy_display}</strong> | Confidence: {confidence_score*100:.0f}% | Risk: {risk_level}</p>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px dashed #a7f3d0; font-size: 13px;">
                        <strong>Expected Profit:</strong> BDT {expected_profit:,.3f} | 
                        <strong>Expected Value:</strong> BDT {expected_profit * win_probability:,.3f}
                    </div>
                </div>
            </div>
            
            <!-- Scenario Analysis -->
            <div class="section">
                <div class="section-title">📊 Multi-Scenario Analysis</div>
                {scenario_table}
            </div>
            
            <!-- Financial Projections -->
            <div class="section">
                <div class="section-title">💰 Financial Projections</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                    <div style="background: #667eea; color: white; padding: 15px; border-radius: 12px; text-align: center;">
                        <div style="font-size: 11px;">Estimated Cost</div>
                        <div style="font-size: 18px; font-weight: bold;">BDT {estimated_cost:,.3f}</div>
                    </div>
                    <div style="background: #10b981; color: white; padding: 15px; border-radius: 12px; text-align: center;">
                        <div style="font-size: 11px;">Expected Profit</div>
                        <div style="font-size: 18px; font-weight: bold;">BDT {expected_profit:,.3f}</div>
                    </div>
                    <div style="background: #f59e0b; color: white; padding: 15px; border-radius: 12px; text-align: center;">
                        <div style="font-size: 11px;">Expected Value</div>
                        <div style="font-size: 18px; font-weight: bold;">BDT {expected_profit * win_probability:,.3f}</div>
                    </div>
                    <div style="background: #ef4444; color: white; padding: 15px; border-radius: 12px; text-align: center;">
                        <div style="font-size: 11px;">Savings vs OCE</div>
                        <div style="font-size: 18px; font-weight: bold;">BDT {official_estimate - recommended_bid:,.3f}</div>
                    </div>
                </div>
            </div>
            
            <!-- Risk Assessment -->
            <div class="section">
                <div class="section-title">⚠️ Risk Assessment</div>
                {risk_assessment}
            </div>
            
            <!-- Detailed Scenarios -->
            <div class="section">
                <div class="section-title">🔍 Detailed Scenario Breakdown</div>
                {detailed_scenarios}
            </div>
            
            <!-- Three-Tier Comparison -->
            <div class="section">
                <div class="section-title">🔄 Three-Tier Analysis Comparison</div>
                {tier_table}
            </div>
            
            <!-- PPR 2025 Calculations -->
            <div class="section">
                <div class="section-title">📐 PPR 2025 Calculation Breakdown</div>
                {calculation_table}
            </div>
        </div>
        
        <div class="footer">
            <strong>Disclaimer:</strong> This analysis complies with Bangladesh PPR 2025 guidelines.<br>
            Final bidding decisions should consider project-specific risks and internal cost structures.<br>
            <strong>Generated for:</strong> {user_name} | {company_name} | Role: {user_role}
        </div>
    </div>
</body>
</html>'''
        return html
    
    def _generate_nppi_table(self, scenarios):
        """Generate NPPI factors per scenario table."""
        if not scenarios:
            return '<p>No scenario data available</p>'
        
        rows = []
        for s in scenarios:
            rows.append(f'''
            <tr>
                <td style="text-align: center;">{s.get('scenario_id', '-')}</td>
                <td style="text-align: center;">{s.get('num_competitors', 0)}</td>
                <td style="text-align: center;"><span class="nppi-badge">{s.get('nppi_factor', 0):.4f}</span></td>
                <td style="text-align: right;">{s.get('slt_threshold', 0):,.3f}</td>
                <td style="text-align: right;">{s.get('optimized_bid', 0):,.3f}</td>
            </tr>
            ''')
        
        return f'''
        <table style="margin-top: 15px;">
            <thead>
                <tr><th>Scenario</th><th>Competitors</th><th>NPPI Factor</th><th>SLT Threshold</th><th>Optimal Bid</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
        '''
    
    def _generate_scenario_table(self, scenarios):
        """Generate scenario summary table with ALL scenarios"""
        if not scenarios:
            return '<p>No scenario data available</p>'
        
        # Risk color mapping
        risk_colors = {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b',
            'HIGH': '#ef4444',
            'MEDIUM-HIGH': '#f97316',
            'MEDIUM-LOW': '#84cc16'
        }
        
        rows = []
        for s in scenarios:
            win_prob = s.get('win_probability', 0)
            risk_level = s.get('risk_level', 'MEDIUM')
            risk_color = risk_colors.get(risk_level, '#f59e0b')
            
            # ✅ Calculate vs OCE comparison
            oce_value = s.get('official_estimate', 0)
            bid_amount = s.get('optimized_bid', 0)
            
            if oce_value > 0:
                bid_ratio_pct = (bid_amount / oce_value) * 100
                less_or_above_than_oce = 100 - bid_ratio_pct
                
                # ✅ Below OCE = Green (⬇️), Above OCE = Red (⬆️)
                if less_or_above_than_oce > 0:
                    comparison_text = f"⬇️ {less_or_above_than_oce:.1f}%"
                    vs_color = "#10b981"  # Green
                else:
                    comparison_text = f"⬆️ {abs(less_or_above_than_oce):.1f}%"
                    vs_color = "#ef4444"  # Red
            else:
                comparison_text = "N/A"
                vs_color = "#6b7280"
            
            rows.append(f'''
            <tr>
                <td style="text-align: center;">{s.get('scenario_id', '-')}</td>
                <td style="text-align: center;">{s.get('num_competitors', 0)}</td>
                <td style="text-align: center; font-family: monospace; font-weight: bold;">{s.get('nppi_factor', 0):.4f}</td>
                <td style="text-align: right; font-family: monospace;">{s.get('optimized_bid', 0):,.3f}</td>
                <td style="text-align: center; font-family: monospace;">{s.get('bid_ratio', 0)*100:.1f}%</td>
                <td style="text-align: center; font-family: monospace; font-weight: bold; color: {vs_color};">{comparison_text}</td>
                <td style="text-align: center;">
                    <div style="background: #e2e8f0; border-radius: 10px; height: 6px; width: 100%;">
                        <div style="background: #3b82f6; width: {win_prob*100:.0f}%; height: 100%; border-radius: 10px;"></div>
                    </div>
                    <span style="font-size: 11px;">{win_prob*100:.0f}%</span>
                </td>
                <td style="text-align: center;">
                    <span class="badge" style="background:{risk_color}20; color:{risk_color};">{risk_level}</span>
                </td>
            </tr>
            ''')
        
        return f'''
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background: #1e3c72; color: white;">
                        <th style="padding: 10px;">#</th>
                        <th style="padding: 10px;">Competitors</th>
                        <th style="padding: 10px;">NPPI</th>
                        <th style="padding: 10px;">Optimal Bid (BDT)</th>
                        <th style="padding: 10px;">Bid Ratio</th>
                        <th style="padding: 10px;">vs OCE</th>
                        <th style="padding: 10px;">Win Probability</th>
                        <th style="padding: 10px;">Risk</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p style="margin-top: 10px; font-size: 11px; color: #666; text-align: center;">
            📊 Showing all {len(scenarios)} scenarios • NPPI factors vary per scenario
        </p>
        '''

    def _generate_scenario_table_bak(self, scenarios):
        """Generate scenario summary table with ALL scenarios"""
        if not scenarios:
            return '<p>No scenario data available</p>'
        
        # Risk color mapping
        risk_colors = {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b',
            'HIGH': '#ef4444',
            'MEDIUM-HIGH': '#f97316',
            'MEDIUM-LOW': '#84cc16'
        }
        
        rows = []
        for s in scenarios:
            win_prob = s.get('win_probability', 0)
            risk_level = s.get('risk_level', 'MEDIUM')
            risk_color = risk_colors.get(risk_level, '#f59e0b')
            
            rows.append(f'''
            <tr>
                <td style="text-align: center;">{s.get('scenario_id', '-')}</td>
                <td style="text-align: center;">{s.get('num_competitors', 0)}</td>
                <td style="text-align: center; font-family: monospace; font-weight: bold;">{s.get('nppi_factor', 0):.4f}</td>
                <td style="text-align: right; font-family: monospace;">{s.get('optimized_bid', 0):,.3f}</td>
                <td style="text-align: center;">{s.get('bid_ratio', 0)*100:.1f}%</td>
                <td style="text-align: center;">
                    <div style="background: #e2e8f0; border-radius: 10px; height: 6px; width: 100%;">
                        <div style="background: #3b82f6; width: {win_prob*100:.0f}%; height: 100%; border-radius: 10px;"></div>
                    </div>
                    <span style="font-size: 11px;">{win_prob*100:.0f}%</span>
                </td>
                <td style="text-align: right; font-family: monospace;">{s.get('expected_profit', 0):,.3f}</td>
                <td style="text-align: center;">
                    <span class="badge" style="background:{risk_color}20; color:{risk_color};">{risk_level}</span>
                </td>
            </tr>
            ''')
        
        return f'''
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background: #1e3c72; color: white;">
                        <th style="padding: 10px;">#</th>
                        <th style="padding: 10px;">Competitors</th>
                        <th style="padding: 10px;">NPPI</th>
                        <th style="padding: 10px;">Optimal Bid (BDT)</th>
                        <th style="padding: 10px;">Bid Ratio</th>
                        <th style="padding: 10px;">Win Probability</th>
                        <th style="padding: 10px;">Expected Profit</th>
                        <th style="padding: 10px;">Risk</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p style="margin-top: 10px; font-size: 11px; color: #666; text-align: center;">
            📊 Showing all {len(scenarios)} scenarios • NPPI factors vary per scenario
        </p>
        '''

    # In modules/price_to_win_html_report_generator.py - Update this method

    def _generate_detailed_scenarios(self, scenarios_full):
        """Generate detailed scenario breakdown with ALL competitor bids - NO TRUNCATION"""
        if not scenarios_full:
            return '<p>No detailed scenario data available</p>'
        
        html = ''
        
        # Show ALL scenarios - no limit
        for scenario in scenarios_full:
            comp_bids = scenario.get('competitor_bids', [])
            stats = scenario.get('competitor_stats', {})
            
            # ✅ Get official_estimate from scenario data
            oce_value = scenario.get('official_estimate', 0)
            bid_amount = scenario.get('optimized_bid', 0)
            
            # ✅ If oce_value is 0, try to get it from the parent object
            if oce_value == 0:
                # Try to get from the first scenario in the list
                for s in scenarios_full:
                    if s.get('official_estimate', 0) > 0:
                        oce_value = s.get('official_estimate', 0)
                        break
            
            # ✅ Calculate vs OCE
            if oce_value > 0:
                bid_ratio_pct = (bid_amount / oce_value) * 100
                less_or_above_than_oce = 100 - bid_ratio_pct
                
                if less_or_above_than_oce > 0:
                    vs_oce_text = f"⬇️ {less_or_above_than_oce:.1f}% below OCE"
                    vs_oce_color = "#10b981"  # Green
                else:
                    vs_oce_text = f"⬆️ {abs(less_or_above_than_oce):.1f}% above OCE"
                    vs_oce_color = "#ef4444"  # Red
            else:
                vs_oce_text = "N/A"
                vs_oce_color = "#6b7280"
            
            # Get zone info if available
            zone_info = ""
            if 'zone' in scenario:
                zone_info = f" | Zone: {scenario.get('zone', 'Default')}"
            
            # Determine risk badge color
            risk_level = scenario.get('risk_level', 'MEDIUM')
            risk_colors = {
                'LOW': '#10b981',
                'MEDIUM': '#f59e0b', 
                'HIGH': '#ef4444',
                'MEDIUM-HIGH': '#f97316',
                'MEDIUM-LOW': '#84cc16'
            }
            risk_color = risk_colors.get(risk_level, '#f59e0b')
            
            # Bid ratio styling
            bid_ratio = scenario.get('bid_ratio', 0)
            ratio_color = '#10b981' if bid_ratio < 0.92 else '#f59e0b' if bid_ratio < 0.95 else '#ef4444'
            
            # Generate competitor bids table
            bid_rows = ''
            if comp_bids:
                # Sort bids for better readability
                sorted_bids = sorted(comp_bids) if isinstance(comp_bids[0], (int, float)) else sorted([b.get('bid', 0) if isinstance(b, dict) else b for b in comp_bids])
                
                for i, bid in enumerate(sorted_bids[:20], 1):
                    # Highlight the optimal bid position
                    optimal_bid = scenario.get('optimized_bid', 0)
                    is_optimal_position = abs(bid - optimal_bid) < (optimal_bid * 0.01)
                    row_style = 'background: #d1fae5;' if is_optimal_position else ''
                    
                    # ✅ Calculate vs OCE for each competitor
                    if oce_value > 0:
                        bid_pct = (bid / oce_value) * 100
                        bid_vs_oce = bid_pct - 100
                        if bid_vs_oce < 0:
                            bid_vs_text = f"⬇️ {abs(bid_vs_oce):.1f}%"
                            bid_vs_color = '#10b981'
                        else:
                            bid_vs_text = f"⬆️ {abs(bid_vs_oce):.1f}%"
                            bid_vs_color = '#ef4444'
                    else:
                        bid_pct = 0
                        bid_vs_text = "N/A"
                        bid_vs_color = '#6b7280'
                    
                    bid_rows += f'''
                    <tr style="{row_style}">
                        <td style="text-align: center;">{i}</td>
                        <td>Competitor {i}</td>
                        <td style="text-align: right; font-family: monospace;">BDT {bid:,.3f}</td>
                        <td style="text-align: center; font-family: monospace;">{bid_pct:.1f}%</td>
                        <td style="text-align: center; font-family: monospace; color: {bid_vs_color};">{bid_vs_text}</td>
                    </tr>
                    '''
            
            # Build competitor stats display
            stats_html = ''
            if stats:
                stats_html = f'''
                <div style="margin: 15px 0; padding: 12px; background: white; border-radius: 8px; display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; font-size: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div><strong>📊 Min:</strong><br>BDT {stats.get('min', 0):,.3f}</div>
                    <div><strong>📈 Max:</strong><br>BDT {stats.get('max', 0):,.3f}</div>
                    <div><strong>📉 Mean:</strong><br>BDT {stats.get('mean', 0):,.3f}</div>
                    <div><strong>📐 Median:</strong><br>BDT {stats.get('median', 0):,.3f}</div>
                    <div><strong>📏 Std Dev:</strong><br>BDT {stats.get('std', 0):,.3f}</div>
                </div>
                '''
            
            html += f'''
            <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 20px; border-left: 4px solid {risk_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 15px;">
                    <h4 style="margin: 0; color: #1e3c72;">
                        📊 Scenario {scenario.get('scenario_id', '?')}: {scenario.get('num_competitors', 0)} Competitors
                        {zone_info}
                    </h4>
                    <span class="badge" style="background:{risk_color}20; color:{risk_color}; padding: 4px 12px; border-radius: 20px;">
                        Risk: {risk_level}
                    </span>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 15px 0; padding: 15px; background: white; border-radius: 10px;">
                    <div>
                        <strong>🎯 Optimal Bid</strong><br>
                        <span style="font-size: 1.1rem; font-weight: bold; color: #667eea;">BDT {scenario.get('optimized_bid', 0):,.3f}</span>
                        <br><small style="color: #666;">{scenario.get('bid_ratio', 0)*100:.1f}% of OCE</small>
                    </div>
                    <div>
                        <strong>📊 vs OCE</strong><br>
                        <span style="font-size: 1.1rem; font-weight: bold; color: {vs_oce_color};">{vs_oce_text}</span>
                    </div>
                    <div>
                        <strong>🏆 Win Probability</strong><br>
                        <span style="font-size: 1.1rem; font-weight: bold; color: #10b981;">{scenario.get('win_probability', 0)*100:.0f}%</span>
                        <br><small style="color: #666;">AI prediction</small>
                    </div>
                    <div>
                        <strong>🛡️ SLT Threshold</strong><br>
                        <span style="font-size: 1.1rem; font-weight: bold;">BDT {scenario.get('slt_threshold', 0):,.3f}</span>
                        <br><small style="color: #666;">PPR 2025 compliant</small>
                    </div>
                </div>
                
                {stats_html}
                
                <div style="margin: 15px 0;">
                    <div style="font-weight: bold; margin-bottom: 10px;">🏢 Competitor Bid Distribution:</div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #e2e8f0;">
                                    <th style="padding: 8px;">#</th>
                                    <th style="padding: 8px;">Competitor</th>
                                    <th style="padding: 8px;">Bid Amount (BDT)</th>
                                    <th style="padding: 8px;">% of OCE</th>
                                    <th style="padding: 8px;">vs OCE</th>
                                </tr>
                            </thead>
                            <tbody>
                                {bid_rows}
                            </tbody>
                        </table>
                    </div>
                    <div style="margin-top: 8px; font-size: 11px; color: #666; text-align: center;">
                        * Highlighted row shows bid closest to optimal recommendation
                    </div>
                </div>
            </div>
            '''
        
        return html

    def _generate_detailed_scenarios_bak(self, scenarios_full):
        """Generate detailed scenario breakdown with competitor bids."""
        if not scenarios_full:
            return '<p>No detailed scenario data available</p>'
        
        html = ''
        for scenario in scenarios_full[:5]:  # Show top 5 scenarios
            comp_bids = scenario.get('competitor_bids', [])
            stats = scenario.get('competitor_stats', {})
            
            bid_rows = ''
            for i, bid in enumerate(comp_bids[:15], 1):
                bid_rows += f'<tr><td style="text-align: center;">{i}</td><td>Competitor {i}</td><td style="text-align: right;">{bid:,.3f}</td></tr>'
            
            html += f'''
            <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                <h4>Scenario {scenario['scenario_id']}: {scenario['num_competitors']} Competitors | NPPI: <span class="nppi-badge">{scenario.get('nppi_factor', 0):.4f}</span></h4>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 15px 0;">
                    <div><strong>Optimal Bid:</strong> BDT {scenario['optimized_bid']:,.3f}</div>
                    <div><strong>Win Prob:</strong> {scenario['win_probability']*100:.0f}%</div>
                    <div><strong>SLT Threshold:</strong> BDT {scenario['slt_threshold']:,.3f}</div>
                    <div><strong>Risk:</strong> {scenario['risk_level']}</div>
                </div>
                <div style="margin: 15px 0; padding: 10px; background: white; border-radius: 8px; display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; font-size: 12px;">
                    <div><strong>Min:</strong> BDT {stats.get('min', 0):,.3f}</div>
                    <div><strong>Max:</strong> BDT {stats.get('max', 0):,.3f}</div>
                    <div><strong>Mean:</strong> BDT {stats.get('mean', 0):,.3f}</div>
                    <div><strong>Median:</strong> BDT {stats.get('median', 0):,.3f}</div>
                    <div><strong>Std Dev:</strong> BDT {stats.get('std', 0):,.3f}</div>
                </div>
                <table style="font-size: 13px;">
                    <thead><tr><th>#</th><th>Competitor</th><th>Bid Amount (BDT)</th></tr></thead>
                    <tbody>{bid_rows}</tbody>
                </table>
            </div>
            '''
        
        if len(scenarios_full) > 5:
            html += f'<p><strong>Plus {len(scenarios_full) - 5} additional scenarios</strong> (full details in application)</p>'
        
        return html
    
    def _generate_competitor_table(self, competitor_bids, official_estimate):
        """Generate competitor comparison table."""
        if not competitor_bids:
            return '<p>No competitor data available</p>'
        
        rows = ''
        for i, comp in enumerate(competitor_bids[:15], 1):
            bid = comp.get('bid', 0) if isinstance(comp, dict) else comp
            pct = (bid / official_estimate * 100) if official_estimate > 0 else 0
            rows += f'<tr><td style="text-align: center;">{i}</td><td>Competitor {i}</td><td style="text-align: right;">{bid:,.3f}</td><td style="text-align: center;">{pct:.2f}%</td></tr>'
        
        return f'''
        <table>
            <thead><tr><th>#</th><th>Competitor</th><th>Bid Amount (BDT)</th><th>% of Estimate</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        '''
    
    def _generate_tier_table(self, tier_comparison):
        """Generate three-tier analysis table."""
        if not tier_comparison:
            return '<p>No tier comparison data available</p>'
        
        rows = ''
        tiers = ['basic', 'advanced', 'enhanced']
        tier_names = {'basic': 'Basic Analysis', 'advanced': 'Advanced (PPR 2025)', 'enhanced': 'Enhanced (ML)'}
        tier_colors = {'basic': '#f8fafc', 'advanced': '#ecfdf5', 'enhanced': '#eff6ff'}
        
        for tier in tiers:
            t = tier_comparison.get(tier, {})
            if not t:
                continue
            rows += f'''
            <tr style="background: {tier_colors[tier]};">
                <td><strong>{tier_names[tier]}</strong></td>
                <td>{t.get('method', 'N/A')[:50]}</td>
                <td style="text-align: right;">{t.get('optimal_bid', 0):,.3f}</td>
                <td style="text-align: center;">{t.get('bid_ratio', 0)*100:.1f}%</td>
                <td style="text-align: center;">{t.get('win_probability', 0)*100:.0f}%</td>
                <td style="text-align: center;">{t.get('confidence_score', 0)*100:.0f}%</td>
                <td style="text-align: center;">{t.get('risk_level', 'N/A')}</td>
            </tr>
            '''
        
        return f'''
        <table>
            <thead><tr><th>Tier</th><th>Method</th><th>Optimal Bid</th><th>Bid Ratio</th><th>Win Prob</th><th>Confidence</th><th>Risk</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        '''
    
    def _generate_calculation_table(self, data, official_estimate):
        """Generate PPR 2025 calculation breakdown."""
        nppi_factor = data.get('nppi_factor', 0.92)
        nppi_price = official_estimate * nppi_factor
        avg_competitor = data.get('avg_competitor', official_estimate * nppi_factor)
        weighted_avg = data.get('weighted_average', official_estimate * 0.94)
        weighted_std = data.get('weighted_std_dev', official_estimate * 0.03)
        slt_threshold = data.get('slt_threshold', weighted_avg - weighted_std)
        recommended_bid = data.get('recommended_bid', slt_threshold * 1.02)
        
        steps = [
            (1, 'Official Estimate (OCE)', 'From tender document', f'BDT {official_estimate:,.3f}', 'Base Value'),
            (2, 'NPPI Factor', f'User configured (min:{data.get("nppi_min", 0.92):.3f} max:{data.get("nppi_max", 0.942):.3f})', f'{nppi_factor:.4f}', 'Index Factor'),
            (3, 'NPPI Price', 'Estimate × NPPI Factor', f'{official_estimate:,.0f} × {nppi_factor:.4f}', f'BDT {nppi_price:,.3f}'),
            (4, 'Average Competitor', 'Σ(Comp Bids) ÷ N', f'({data.get("competitor_count", 0)} bids)', f'BDT {avg_competitor:,.3f}'),
            (5, 'Weighted Average (X̄)', '0.5(Avg) + 0.2(Est) + 0.3(NPPI)', f'0.5×{avg_competitor:,.0f} + 0.2×{official_estimate:,.0f} + 0.3×{nppi_price:,.0f}', f'BDT {weighted_avg:,.3f}'),
            (6, 'Standard Deviation (Sd)', '√[Σ(x̄ - xᵢ)²/(n-1)]', f'σ = {weighted_std:.3f}', f'BDT {weighted_std:,.3f}'),
            (7, 'SLT Threshold', 'X̄ - Sd', f'{weighted_avg:,.0f} - {weighted_std:,.0f}', f'BDT {slt_threshold:,.3f}'),
            (8, 'AI Recommended Bid', 'AI Optimization Engine', 'Based on win probability analysis', f'BDT {recommended_bid:,.3f}'),
            (9, 'PPR 2025 Compliance', 'Bid ≥ SLT?', f'{recommended_bid:,.0f} ≥ {slt_threshold:,.0f}', '<strong style="color:#10b981">✅ PASS</strong>' if recommended_bid >= slt_threshold else '<strong style="color:#ef4444">❌ FAIL</strong>')
        ]
        
        rows = ''
        for step in steps:
            rows += f'''
            <tr>
                <td style="text-align: center; background:#f8fafc;">{step[0]}</td>
                <td><strong>{step[1]}</strong><br><span style="font-size: 11px; color:#64748b;">{step[2]}</span></td>
                <td style="text-align: right; font-family: monospace;">{step[3]}</td>
                <td><strong>{step[4]}</strong></td>
            </tr>
            '''
        
        return f'<table><thead><tr><th>Step</th><th>Description</th><th>Calculation</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>'
    
    def _generate_risk_assessment(self, risk_level, bid_ratio):
        """Generate risk assessment section."""
        risk_score = int((1 - bid_ratio) * 500) if bid_ratio else 50
        risk_score = min(100, max(0, risk_score))
        
        configs = {
            'LOW': {'color': '#10b981', 'bg': '#ecfdf5', 'icon': '🟢', 'title': 'Low Risk Profile', 'desc': 'Conservative strategy with high profit margin.'},
            'MEDIUM': {'color': '#f59e0b', 'bg': '#fef3c7', 'icon': '🟡', 'title': 'Medium Risk Profile', 'desc': 'Balanced approach for most tenders.'},
            'HIGH': {'color': '#ef4444', 'bg': '#fee2e2', 'icon': '🔴', 'title': 'High Risk Profile', 'desc': 'Aggressive strategy prioritizing win probability.'}
        }
        cfg = configs.get(risk_level, configs['MEDIUM'])
        
        return f'''
        <div style="background: {cfg['bg']}; border-left: 5px solid {cfg['color']}; padding: 20px; border-radius: 12px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 32px;">{cfg['icon']}</span>
                <div><strong style="font-size: 18px; color: {cfg['color']};">{cfg['title']}</strong><br>Risk Score: {risk_score}/100</div>
            </div>
            <p>{cfg['desc']}</p>
            <div style="margin-top: 15px;">
                <div style="background: #e2e8f0; border-radius: 10px; height: 8px;">
                    <div style="background: {cfg['color']}; width: {risk_score}%; height: 100%; border-radius: 10px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 10px;">
                    <span>Conservative</span><span>Balanced</span><span>Aggressive</span>
                </div>
            </div>
        </div>
        '''
    
    def save_to_file(self, filepath):
        """Save HTML report to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_html())
    
    def get_download_link(self, filename=None):
        """Get HTML download link."""
        if not filename:
            filename = f"price_to_win_report_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.html"
        b64 = base64.b64encode(self.generate_html().encode()).decode()
        return f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Download HTML Report</a>'


def render_report_section(analysis_data):
    """Render report download section in Streamlit."""
    from modules.rbac import can_export_data
    
    if not can_export_data():
        st.info("🔒 Export reports available on Professional and Enterprise plans")
        return
    
    st.markdown("---")
    st.markdown("## 📄 Export Report")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Generate HTML Report", use_container_width=True, type="primary"):
            with st.spinner("Generating report..."):
                generator = HTMLReportGenerator(analysis_data)
                html = generator.generate_html()
                b64 = base64.b64encode(html.encode()).decode()
                filename = f"price_to_win_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                st.session_state.report_html = {'b64': b64, 'filename': filename}
                st.success("✅ Report ready! Click download below.")
    
    if st.session_state.get('report_html'):
        r = st.session_state.report_html
        st.markdown(f'<a href="data:text/html;base64,{r["b64"]}" download="{r["filename"]}"><button style="background:#10b981; color:white; padding:10px 20px; border:none; border-radius:8px; cursor:pointer; width:100%;">📥 Download HTML Report</button></a>', unsafe_allow_html=True)
    
    with col2:
        if st.button("📄 Export CSV", use_container_width=True):
            df = pd.DataFrame([{
                'Metric': 'Recommended Bid', 'Value': analysis_data.get('recommended_bid', 0)
            }])
            st.download_button("Download CSV", df.to_csv(index=False), f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", use_container_width=True)
    
    with col3:
        if st.button("📋 Export JSON", use_container_width=True):
            import json
            json_str = json.dumps(analysis_data, indent=2, default=str)
            st.download_button("Download JSON", json_str, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", use_container_width=True)