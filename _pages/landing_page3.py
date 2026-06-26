# _pages/landing_page.py

import streamlit as st
from version import get_app_name, get_app_desc

import base64
import os
from modules.landing_counters import render_all_counters
from pathlib import Path


# # 1. Safely locate and load your local image file bytes
# current_dir = Path(__file__).parent
# image_path = current_dir / "assets" / "images" / "cptuEgpLogo.gif"

# if image_path.exists():
#     st.image(str(image_path), use_container_width=True)
# else:
#     st.warning("Logo image not found")

def get_logo_html():
    """Get CPTU e-GP Logo with fallback to GitHub"""
    
    current_dir = Path(__file__).parent
    image_path = current_dir / "assets" / "images" / "cptuEgpLogo.gif"
    
    if image_path.exists():
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/gif;base64,{encoded}"
    
    # Fallback to GitHub raw URL
    return "https://raw.githubusercontent.com/shomonrobie/iTender/main/assets/images/cptuEgpLogo.gif"

# if os.path.exists(image_path):
#     with open(image_path, "rb") as image_file:
#         encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
#     # Generate the correct base64 data URI format for a GIF
#     img_src = f"data:image/gif;base64,{encoded_string}"
# else:
#     # Fallback placeholder string if file path is temporarily mislocated
#     img_src = ""
img_src = get_logo_html()

# In your landing page / home page
def render_workflow_section():
    """Render horizontal animated workflow section using Streamlit columns"""
    
    st.markdown("""
    <style>
        .workflow-section {
            padding: 2.5rem 1rem 3rem 1rem;
            margin: 2rem 0;
            background: linear-gradient(135deg, #f8f9fe 0%, #eef0f7 50%, #e8e6f0 100%);
            border-radius: 28px;
            position: relative;
            overflow: hidden;
        }
        .workflow-section::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -30%;
            width: 100%;
            height: 150%;
            background: radial-gradient(ellipse at 70% 50%, rgba(118, 75, 162, 0.06) 0%, transparent 70%);
            pointer-events: none;
        }
        .workflow-header {
            text-align: center;
            margin-bottom: 2.5rem;
            position: relative;
            z-index: 1;
        }

        .workflow-header h2 {
            font-size: 2.6rem !important;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.3rem;
            animation: fadeInUp 0.8s ease-out 0.6s both;                
        }
        .workflow-header h2 span {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .workflow-header p {
            color: #6c757d;
            font-size: 1.05rem;
        }
        .workflow-step-card {
            background: white;
            border-radius: 20px;
            padding: 20px 12px 18px;
            text-align: center;
            box-shadow: 0 4px 25px rgba(0,0,0,0.06);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            height: 100%;
            border-bottom: 4px solid transparent;
            position: relative;
            overflow: hidden;
        }
        .workflow-step-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 16px 50px rgba(0,0,0,0.12);
        }
        .workflow-step-card .step-icon {
            width: 65px;
            height: 65px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 12px;
            font-size: 28px;
            transition: all 0.4s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        }
        .workflow-step-card:hover .step-icon {
            transform: scale(1.1) rotate(-5deg);
        }
        .workflow-step-card .step-number {
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 12px;
            border-radius: 20px;
            margin-bottom: 6px;
            color: white;
        }
        .workflow-step-card .step-title {
            font-size: 15px;
            font-weight: 700;
            color: #1a1a2e;
            margin: 4px 0 2px;
        }
        .workflow-step-card .step-desc {
            font-size: 11px;
            color: #6c757d;
            margin: 0;
            line-height: 1.3;
        }
        .workflow-step-card .step-glow {
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            border-radius: 50%;
            opacity: 0;
            transition: opacity 0.6s ease;
            pointer-events: none;
        }
        .workflow-step-card:hover .step-glow {
            opacity: 0.1;
        }
        /* Step colors */
        .step-1 .step-icon { background: linear-gradient(135deg, #e3f2fd, #bbdefb); }
        .step-1 .step-number { background: linear-gradient(135deg, #2196F3, #1565C0); }
        .step-1 .step-glow { background: radial-gradient(circle, #2196F3 0%, transparent 70%); }
        .step-1:hover { border-bottom-color: #2196F3; }
        
        .step-2 .step-icon { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); }
        .step-2 .step-number { background: linear-gradient(135deg, #4CAF50, #2E7D32); }
        .step-2 .step-glow { background: radial-gradient(circle, #4CAF50 0%, transparent 70%); }
        .step-2:hover { border-bottom-color: #4CAF50; }
        
        .step-3 .step-icon { background: linear-gradient(135deg, #fff3e0, #ffe0b2); }
        .step-3 .step-number { background: linear-gradient(135deg, #FF9800, #E65100); }
        .step-3 .step-glow { background: radial-gradient(circle, #FF9800 0%, transparent 70%); }
        .step-3:hover { border-bottom-color: #FF9800; }
        
        .step-4 .step-icon { background: linear-gradient(135deg, #fce4ec, #f8bbd0); }
        .step-4 .step-number { background: linear-gradient(135deg, #E91E63, #880E4F); }
        .step-4 .step-glow { background: radial-gradient(circle, #E91E63 0%, transparent 70%); }
        .step-4:hover { border-bottom-color: #E91E63; }
        
        .step-5 .step-icon { background: linear-gradient(135deg, #f3e5f5, #e1bee7); }
        .step-5 .step-number { background: linear-gradient(135deg, #9C27B0, #4A148C); }
        .step-5 .step-glow { background: radial-gradient(circle, #9C27B0 0%, transparent 70%); }
        .step-5:hover { border-bottom-color: #9C27B0; }
        
        .workflow-arrow {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: #4CAF50;
            opacity: 0.6;
            padding: 0 5px;
        }
        @media (max-width: 768px) {
            .workflow-step-card .step-icon { width: 50px; height: 50px; font-size: 22px; }
            .workflow-step-card .step-title { font-size: 13px; }
            .workflow-step-card .step-desc { font-size: 10px; }
            .workflow-header h2 { font-size: 1.5rem; }
            .workflow-arrow { font-size: 18px; }
        }
        @media (max-width: 576px) {
            .workflow-step-card { padding: 15px 8px; }
            .workflow-step-card .step-icon { width: 40px; height: 40px; font-size: 18px; margin-bottom: 8px; }
            .workflow-step-card .step-title { font-size: 11px; }
            .workflow-step-card .step-desc { font-size: 9px; }
            .workflow-arrow { font-size: 14px; }
        }
    </style>
    
    <div class="workflow-section">
        <div class="workflow-header">
            <h2>🚀 <span>Easy & Complete</span> Bidding Workflow</h2>
            <p>From tender creation to winning bid – all in one platform</p>
        </div>
    """, unsafe_allow_html=True)
    
    steps = [
        {"icon": "📋", "number": "1", "title": "Create Tender", "desc": "Add tender details & requirements", "class": "step-1"},
        {"icon": "📄", "number": "2", "title": "Generate BOQ", "desc": "Create detailed Bill of Quantities", "class": "step-2"},
        {"icon": "👥", "number": "3", "title": "Add Competitors", "desc": "Track & analyze competition", "class": "step-3"},
        {"icon": "🎯", "number": "4", "title": "Optimize Bid", "desc": "AI-powered bid optimization", "class": "step-4"},
        {"icon": "🏆", "number": "5", "title": "Submit & Win", "desc": "Submit winning bid confidently", "class": "step-5"}
    ]
    
    # Use Streamlit columns for horizontal layout
    cols = st.columns(5)
    
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            st.markdown(f"""
            <div class="workflow-step-card {step['class']}">
                <div class="step-glow"></div>
                <div class="step-number">{step['number']}</div>
                <div class="step-icon">{step['icon']}</div>
                <div class="step-title">{step['title']}</div>
                <div class="step-desc">{step['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add arrow between steps (except after last)
            if i < len(steps) - 1:
                # We can't put HTML between Streamlit columns easily
                # So we add a small arrow indicator below
                pass
    
    # Add arrow indicators between steps using a separate row
    st.markdown("""
    <div style="display: flex; justify-content: space-between; padding: 0 20px; margin-top: -5px;">
        <span style="flex:1; text-align:center; color: #4CAF50; font-size: 20px;">▶</span>
        <span style="flex:1; text-align:center; color: #4CAF50; font-size: 20px;">▶</span>
        <span style="flex:1; text-align:center; color: #4CAF50; font-size: 20px;">▶</span>
        <span style="flex:1; text-align:center; color: #4CAF50; font-size: 20px;">▶</span>
        <span style="flex:1; text-align:center; color: transparent;">⬤</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
def render_workflow_section3():
    """Render horizontal animated workflow section with step cards and gradients"""
    
    st.markdown("""
    <style>
        .workflow-container {
            background: linear-gradient(135deg, #f8f9fe 0%, #eef0f7 50%, #e8e6f0 100%);
            border-radius: 28px;
            padding: 2.5rem 2rem 3rem 2rem;
            margin: 2rem 0 3rem 0;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.06);
        }
        .workflow-container::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -30%;
            width: 60%;
            height: 150%;
            background: radial-gradient(ellipse at 70% 50%, rgba(118, 75, 162, 0.06) 0%, transparent 70%);
            pointer-events: none;
        }
        .workflow-header {
            text-align: center;
            margin-bottom: 2.5rem;
            position: relative;
            z-index: 1;
        }
        .workflow-header .workflow-badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(118, 75, 162, 0.12), rgba(102, 126, 234, 0.12));
            padding: 0.3rem 1.5rem;
            border-radius: 30px;
            font-size: 0.8rem;
            color: #5a3d8a;
            font-weight: 600;
            margin-bottom: 0.8rem;
            border: 1px solid rgba(118, 75, 162, 0.15);
        }
        .workflow-header h2 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.3rem;
        }
        .workflow-header h2 span {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .workflow-header p {
            color: #6c757d;
            font-size: 1.05rem;
        }
        
        /* Step Cards */
        .step-card {
            background: white;
            border-radius: 20px;
            padding: 24px 16px 20px;
            text-align: center;
            box-shadow: 0 4px 25px rgba(0,0,0,0.06);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            height: 100%;
            border-bottom: 4px solid transparent;
            position: relative;
            overflow: hidden;
        }
        .step-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0;
            transition: opacity 0.5s ease;
            border-radius: 20px;
        }
        .step-card:hover {
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 20px 60px rgba(0,0,0,0.12);
        }
        .step-card:hover::before {
            opacity: 1;
        }
        .step-card .step-number {
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 14px;
            border-radius: 20px;
            margin-bottom: 8px;
            color: white;
            position: relative;
            z-index: 1;
        }
        .step-card .step-icon {
            width: 68px;
            height: 68px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 12px;
            font-size: 30px;
            transition: all 0.4s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.06);
            position: relative;
            z-index: 1;
        }
        .step-card:hover .step-icon {
            transform: scale(1.1) rotate(-5deg);
        }
        .step-card .step-title {
            font-size: 16px;
            font-weight: 700;
            color: #1a1a2e;
            margin: 4px 0 2px;
            position: relative;
            z-index: 1;
        }
        .step-card .step-desc {
            font-size: 12px;
            color: #6c757d;
            margin: 0;
            line-height: 1.4;
            position: relative;
            z-index: 1;
        }
        .step-card .step-glow {
            position: absolute;
            top: -30%;
            left: -30%;
            width: 160%;
            height: 160%;
            border-radius: 50%;
            opacity: 0;
            transition: opacity 0.6s ease;
            pointer-events: none;
        }
        .step-card:hover .step-glow {
            opacity: 0.08;
        }
        
        /* Step 1 - Blue */
        .step-1 .step-icon { background: linear-gradient(135deg, #e3f2fd, #bbdefb); }
        .step-1 .step-number { background: linear-gradient(135deg, #2196F3, #1565C0); }
        .step-1 .step-glow { background: radial-gradient(circle, #2196F3 0%, transparent 70%); }
        .step-1:hover { border-bottom-color: #2196F3; }
        .step-1:hover .step-icon { box-shadow: 0 8px 30px rgba(33, 150, 243, 0.3); }
        
        /* Step 2 - Green */
        .step-2 .step-icon { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); }
        .step-2 .step-number { background: linear-gradient(135deg, #4CAF50, #2E7D32); }
        .step-2 .step-glow { background: radial-gradient(circle, #4CAF50 0%, transparent 70%); }
        .step-2:hover { border-bottom-color: #4CAF50; }
        .step-2:hover .step-icon { box-shadow: 0 8px 30px rgba(76, 175, 80, 0.3); }
        
        /* Step 3 - Orange */
        .step-3 .step-icon { background: linear-gradient(135deg, #fff3e0, #ffe0b2); }
        .step-3 .step-number { background: linear-gradient(135deg, #FF9800, #E65100); }
        .step-3 .step-glow { background: radial-gradient(circle, #FF9800 0%, transparent 70%); }
        .step-3:hover { border-bottom-color: #FF9800; }
        .step-3:hover .step-icon { box-shadow: 0 8px 30px rgba(255, 152, 0, 0.3); }
        
        /* Step 4 - Pink */
        .step-4 .step-icon { background: linear-gradient(135deg, #fce4ec, #f8bbd0); }
        .step-4 .step-number { background: linear-gradient(135deg, #E91E63, #880E4F); }
        .step-4 .step-glow { background: radial-gradient(circle, #E91E63 0%, transparent 70%); }
        .step-4:hover { border-bottom-color: #E91E63; }
        .step-4:hover .step-icon { box-shadow: 0 8px 30px rgba(233, 30, 99, 0.3); }
        
        /* Step 5 - Purple */
        .step-5 .step-icon { background: linear-gradient(135deg, #f3e5f5, #e1bee7); }
        .step-5 .step-number { background: linear-gradient(135deg, #9C27B0, #4A148C); }
        .step-5 .step-glow { background: radial-gradient(circle, #9C27B0 0%, transparent 70%); }
        .step-5:hover { border-bottom-color: #9C27B0; }
        .step-5:hover .step-icon { box-shadow: 0 8px 30px rgba(156, 39, 176, 0.3); }
        
        .step-connector {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            padding: 0 4px;
        }
        .step-connector .arrow {
            font-size: 22px;
            color: #4CAF50;
            opacity: 0.5;
            animation: pulseArrow 1.8s ease-in-out infinite;
        }
        @keyframes pulseArrow {
            0%, 100% { opacity: 0.5; transform: translateX(0); }
            50% { opacity: 1; transform: translateX(4px); }
        }
        
        /* Responsive */
        @media (max-width: 992px) {
            .workflow-container { padding: 2rem 1rem; }
            .step-card { padding: 18px 12px 16px; }
            .step-card .step-icon { width: 54px; height: 54px; font-size: 24px; }
            .step-card .step-title { font-size: 14px; }
            .step-card .step-desc { font-size: 11px; }
            .workflow-header h2 { font-size: 1.6rem; }
            .step-connector .arrow { font-size: 18px; }
        }
        @media (max-width: 576px) {
            .workflow-container { padding: 1.5rem 0.5rem; }
            .step-card { padding: 14px 8px 12px; }
            .step-card .step-icon { width: 44px; height: 44px; font-size: 20px; margin-bottom: 8px; }
            .step-card .step-title { font-size: 12px; }
            .step-card .step-desc { font-size: 10px; }
            .workflow-header h2 { font-size: 1.3rem; }
            .step-connector .arrow { font-size: 14px; }
        }
    </style>
    
    <div class="workflow-container">
        <div class="workflow-header">
            <div class="workflow-badge">🚀 BIDDING WORKFLOW</div>
            <h2>🚀 <span>Easy & Complete</span> Bidding Workflow</h2>
            <p>From tender creation to winning bid – all in one platform</p>
        </div>
    """, unsafe_allow_html=True)
    
    steps = [
        {"icon": "📋", "number": "1", "title": "Create Tender", "desc": "Add tender details & requirements", "class": "step-1"},
        {"icon": "📄", "number": "2", "title": "Generate BOQ", "desc": "Create detailed Bill of Quantities", "class": "step-2"},
        {"icon": "👥", "number": "3", "title": "Add Competitors", "desc": "Track & analyze competition", "class": "step-3"},
        {"icon": "🎯", "number": "4", "title": "Optimize Bid", "desc": "AI-powered bid optimization", "class": "step-4"},
        {"icon": "🏆", "number": "5", "title": "Submit & Win", "desc": "Submit winning bid confidently", "class": "step-5"}
    ]
    
    # Create columns with connectors between them
    # We need 9 columns: step, connector, step, connector, step, connector, step, connector, step
    # But simpler: use 5 columns for steps and add connectors as a separate row
    
    # Row 1: Steps
    cols = st.columns(5)
    
    for col, step in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div class="step-card {step['class']}">
                <div class="step-glow"></div>
                <div class="step-number">{step['number']}</div>
                <div class="step-icon">{step['icon']}</div>
                <div class="step-title">{step['title']}</div>
                <div class="step-desc">{step['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Row 2: Connectors (arrows between steps)
    # Use 5 columns with arrows in between
    st.markdown("""
    <div style="display: flex; justify-content: space-between; padding: 0 20px; margin-top: 4px;">
        <div style="flex:1; text-align:center; color: #4CAF50; font-size: 20px; opacity:0.4;">▶</div>
        <div style="flex:1; text-align:center; color: #4CAF50; font-size: 20px; opacity:0.4;">▶</div>
        <div style="flex:1; text-align:center; color: #4CAF50; font-size: 20px; opacity:0.4;">▶</div>
        <div style="flex:1; text-align:center; color: #4CAF50; font-size: 20px; opacity:0.4;">▶</div>
        <div style="flex:1; text-align:center; color: transparent; font-size: 20px;">⬤</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_workflow_section_with_connectors():
    """Render workflow with animated connectors between steps"""
    
    st.markdown("""
    <style>
        .workflow-container {
            background: linear-gradient(135deg, #f8f9fe 0%, #eef0f7 50%, #e8e6f0 100%);
            border-radius: 28px;
            padding: 2.5rem 2rem 3rem 2rem;
            margin: 2rem 0 3rem 0;
            position: relative;
            overflow: hidden;
        }
        .workflow-header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .workflow-header .badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(118, 75, 162, 0.12), rgba(102, 126, 234, 0.12));
            padding: 0.3rem 1.5rem;
            border-radius: 30px;
            font-size: 0.8rem;
            color: #5a3d8a;
            font-weight: 600;
            margin-bottom: 0.8rem;
        }
        .workflow-header h2 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1a1a2e;
        }
        .workflow-header h2 span {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .workflow-header p {
            color: #6c757d;
            font-size: 1.05rem;
        }
        .step-card {
            background: white;
            border-radius: 20px;
            padding: 20px 12px 16px;
            text-align: center;
            box-shadow: 0 4px 25px rgba(0,0,0,0.06);
            transition: all 0.4s ease;
            height: 100%;
            border-bottom: 4px solid transparent;
            position: relative;
            overflow: hidden;
        }
        .step-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 60px rgba(0,0,0,0.12);
        }
        .step-card .icon {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 10px;
            font-size: 28px;
            transition: transform 0.4s ease;
        }
        .step-card:hover .icon {
            transform: scale(1.1) rotate(-5deg);
        }
        .step-card .num {
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 12px;
            border-radius: 20px;
            color: white;
            margin-bottom: 4px;
        }
        .step-card .title {
            font-size: 14px;
            font-weight: 700;
            color: #1a1a2e;
        }
        .step-card .desc {
            font-size: 11px;
            color: #6c757d;
            margin-top: 2px;
        }
        .step-card .glow {
            position: absolute;
            top: -30%;
            left: -30%;
            width: 160%;
            height: 160%;
            border-radius: 50%;
            opacity: 0;
            transition: opacity 0.6s ease;
            pointer-events: none;
        }
        .step-card:hover .glow { opacity: 0.08; }
        
        .step-1 .icon { background: linear-gradient(135deg, #e3f2fd, #bbdefb); }
        .step-1 .num { background: linear-gradient(135deg, #2196F3, #1565C0); }
        .step-1 .glow { background: radial-gradient(circle, #2196F3 0%, transparent 70%); }
        .step-1:hover { border-bottom-color: #2196F3; }
        
        .step-2 .icon { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); }
        .step-2 .num { background: linear-gradient(135deg, #4CAF50, #2E7D32); }
        .step-2 .glow { background: radial-gradient(circle, #4CAF50 0%, transparent 70%); }
        .step-2:hover { border-bottom-color: #4CAF50; }
        
        .step-3 .icon { background: linear-gradient(135deg, #fff3e0, #ffe0b2); }
        .step-3 .num { background: linear-gradient(135deg, #FF9800, #E65100); }
        .step-3 .glow { background: radial-gradient(circle, #FF9800 0%, transparent 70%); }
        .step-3:hover { border-bottom-color: #FF9800; }
        
        .step-4 .icon { background: linear-gradient(135deg, #fce4ec, #f8bbd0); }
        .step-4 .num { background: linear-gradient(135deg, #E91E63, #880E4F); }
        .step-4 .glow { background: radial-gradient(circle, #E91E63 0%, transparent 70%); }
        .step-4:hover { border-bottom-color: #E91E63; }
        
        .step-5 .icon { background: linear-gradient(135deg, #f3e5f5, #e1bee7); }
        .step-5 .num { background: linear-gradient(135deg, #9C27B0, #4A148C); }
        .step-5 .glow { background: radial-gradient(circle, #9C27B0 0%, transparent 70%); }
        .step-5:hover { border-bottom-color: #9C27B0; }
        
        .connector-wrapper {
            display: flex;
            justify-content: space-between;
            padding: 0 10px;
            margin-top: 5px;
        }
        .connector-wrapper .arrow {
            flex: 1;
            text-align: center;
            font-size: 18px;
            color: #4CAF50;
            opacity: 0.4;
            animation: arrowPulse 1.8s ease-in-out infinite;
        }
        .connector-wrapper .arrow:nth-child(1) { animation-delay: 0s; }
        .connector-wrapper .arrow:nth-child(2) { animation-delay: 0.3s; }
        .connector-wrapper .arrow:nth-child(3) { animation-delay: 0.6s; }
        .connector-wrapper .arrow:nth-child(4) { animation-delay: 0.9s; }
        
        @keyframes arrowPulse {
            0%, 100% { opacity: 0.4; transform: translateX(0); }
            50% { opacity: 0.9; transform: translateX(4px); }
        }
    </style>
    <div class="workflow-section">
        <div class="workflow-header">
            <h2>🚀 <span>Easy & Complete</span> Bidding Workflow</h2>
            <p>From tender creation to winning bid – all in one platform</p>
        </div>
    """, unsafe_allow_html=True)
    
    steps = [
        {"icon": "📋", "num": "1", "title": "Create Tender", "desc": "Add tender details", "class": "s1"},
        {"icon": "📄", "num": "2", "title": "Generate BOQ", "desc": "Create Bill of Quantities", "class": "s2"},
        {"icon": "👥", "num": "3", "title": "Add Competitors", "desc": "Track competition", "class": "s3"},
        {"icon": "🎯", "num": "4", "title": "Optimize Bid", "desc": "AI-powered bidding", "class": "s4"},
        {"icon": "🏆", "num": "5", "title": "Submit & Win", "desc": "Win confidently", "class": "s5"}
    ]
    
    # Create 5 columns
    cols = st.columns(5)
    
    for col, step in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div class="step-card {step['class']}">
                <div class="num">{step['num']}</div>
                <div class="icon">{step['icon']}</div>
                <div class="title">{step['title']}</div>
                <div class="desc">{step['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
def render_workflow_section2():
    """Render horizontal workflow with Streamlit columns and connectors"""
    
    st.markdown("""
    <style>
        .workflow-section {
            padding: 2.5rem 1rem 3rem 1rem;
            margin: 2rem 0;
            background: linear-gradient(135deg, #f8f9fe 0%, #eef0f7 50%, #e8e6f0 100%);
            border-radius: 28px;
        }
        .workflow-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .workflow-header h2 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1a1a2e;
        }
        .workflow-header h2 span {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .workflow-header p {
            color: #6c757d;
            font-size: 1.05rem;
        }
        .step-card {
            background: white;
            border-radius: 20px;
            padding: 20px 10px 16px;
            text-align: center;
            box-shadow: 0 4px 25px rgba(0,0,0,0.06);
            transition: all 0.4s ease;
            height: 100%;
            border-bottom: 4px solid transparent;
        }
        .step-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 16px 50px rgba(0,0,0,0.12);
        }
        .step-card .icon {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 10px;
            font-size: 26px;
            transition: transform 0.4s ease;
        }
        .step-card:hover .icon {
            transform: scale(1.1) rotate(-5deg);
        }
        .step-card .num {
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: 20px;
            margin-bottom: 4px;
            color: white;
        }
        .step-card .title {
            font-size: 14px;
            font-weight: 700;
            color: #1a1a2e;
        }
        .step-card .desc {
            font-size: 10px;
            color: #6c757d;
            margin-top: 2px;
        }
        .s1 .icon { background: linear-gradient(135deg, #e3f2fd, #bbdefb); }
        .s1 .num { background: linear-gradient(135deg, #2196F3, #1565C0); }
        .s1:hover { border-bottom-color: #2196F3; }
        
        .s2 .icon { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); }
        .s2 .num { background: linear-gradient(135deg, #4CAF50, #2E7D32); }
        .s2:hover { border-bottom-color: #4CAF50; }
        
        .s3 .icon { background: linear-gradient(135deg, #fff3e0, #ffe0b2); }
        .s3 .num { background: linear-gradient(135deg, #FF9800, #E65100); }
        .s3:hover { border-bottom-color: #FF9800; }
        
        .s4 .icon { background: linear-gradient(135deg, #fce4ec, #f8bbd0); }
        .s4 .num { background: linear-gradient(135deg, #E91E63, #880E4F); }
        .s4:hover { border-bottom-color: #E91E63; }
        
        .s5 .icon { background: linear-gradient(135deg, #f3e5f5, #e1bee7); }
        .s5 .num { background: linear-gradient(135deg, #9C27B0, #4A148C); }
        .s5:hover { border-bottom-color: #9C27B0; }
        
        .connector-row {
            display: flex;
            justify-content: space-between;
            padding: 0 10px;
            margin-top: -2px;
        }
        .connector-row span {
            flex: 1;
            text-align: center;
            font-size: 14px;
            color: #4CAF50;
            opacity: 0.5;
        }
        @media (max-width: 768px) {
            .step-card { padding: 15px 8px; }
            .step-card .icon { width: 45px; height: 45px; font-size: 20px; }
            .step-card .title { font-size: 12px; }
            .step-card .desc { font-size: 9px; }
            .workflow-header h2 { font-size: 1.5rem; }
        }
    </style>
    
    <div class="workflow-section">
        <div class="workflow-header">
            <h2>🚀 <span>Easy & Complete</span> Bidding Workflow</h2>
            <p>From tender creation to winning bid – all in one platform</p>
        </div>
    """, unsafe_allow_html=True)
    
    steps = [
        {"icon": "📋", "num": "1", "title": "Create Tender", "desc": "Add tender details", "class": "s1"},
        {"icon": "📄", "num": "2", "title": "Generate BOQ", "desc": "Create Bill of Quantities", "class": "s2"},
        {"icon": "👥", "num": "3", "title": "Add Competitors", "desc": "Track competition", "class": "s3"},
        {"icon": "🎯", "num": "4", "title": "Optimize Bid", "desc": "AI-powered bidding", "class": "s4"},
        {"icon": "🏆", "num": "5", "title": "Submit & Win", "desc": "Win confidently", "class": "s5"}
    ]
    
    # Create 5 columns
    cols = st.columns(5)
    
    for col, step in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div class="step-card {step['class']}">
                <div class="num">{step['num']}</div>
                <div class="icon">{step['icon']}</div>
                <div class="title">{step['title']}</div>
                <div class="desc">{step['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def show_landing_page():
    """Unified landing page with English and Bangla content - Modern & Professional"""
    
    st.set_page_config(page_title="TenderAI (BD) - AI Tender Intelligence Platform", page_icon="🏗️", layout="wide")
    
    # Modern CSS with Animations
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Hind+Siliguri:wght@300;400;500;600;700&display=swap');
    
    /* Global Reset & Base */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    .main .stMarkdown, .main div, .main p, .main span, .main label {
        font-family: 'Inter', 'Hind Siliguri', sans-serif !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
    }
    
    /* Smooth Scroll */
    html {
        scroll-behavior: smooth;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu, header, footer {
        visibility: hidden;
    }
    
    /* ==================== ANIMATIONS ==================== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes fadeInRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    @keyframes slideInScale {
        from {
            opacity: 0;
            transform: scale(0.9);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    @keyframes borderGlow {
        0%, 100% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
        50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.8), 0 0 40px rgba(59, 130, 246, 0.4); }
    }
    
    @keyframes typing {
        from { width: 0; }
        to { width: 100%; }
    }
    
    @keyframes blink {
        50% { border-color: transparent; }
    }
    
    @keyframes ripple {
        0% { transform: scale(0); opacity: 1; }
        100% { transform: scale(4); opacity: 0; }
    }
    
    @keyframes particleFloat {
        0%, 100% { transform: translate(0, 0) rotate(0deg); opacity: 0.6; }
        25% { transform: translate(50px, -50px) rotate(90deg); opacity: 0.3; }
        50% { transform: translate(0, -100px) rotate(180deg); opacity: 0.6; }
        75% { transform: translate(-50px, -50px) rotate(270deg); opacity: 0.3; }
    }
    
    /* ==================== ANIMATED BACKGROUND ==================== */
    .animated-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        overflow: hidden;
    }
    
    .animated-bg::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.03) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
                    radial-gradient(circle at 20% 80%, rgba(6, 182, 212, 0.03) 0%, transparent 50%);
        animation: rotate 60s linear infinite;
    }
    
    .floating-shape {
        position: absolute;
        border-radius: 50%;
        opacity: 0.1;
        animation: particleFloat 20s infinite;
    }
    
    .floating-shape:nth-child(1) {
        width: 80px;
        height: 80px;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        top: 20%;
        left: 10%;
        animation-delay: 0s;
    }
    
    .floating-shape:nth-child(2) {
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #06b6d4, #3b82f6);
        top: 60%;
        right: 15%;
        animation-delay: -5s;
    }
    
    .floating-shape:nth-child(3) {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        bottom: 20%;
        left: 30%;
        animation-delay: -10s;
    }
    
    /* ==================== NAVIGATION BAR ==================== */
    .navbar {
        position: sticky;
        top: 0;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.6s ease-out;
    }
    
    .nav-logo {
        font-size: 1.5rem !important;
        font-weight: 800;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .nav-links {
        display: flex;
        gap: 2rem;
        list-style: none;
    }
    
    .nav-links a {
        text-decoration: none;
        color: #475569;
        font-weight: 500;
        font-size: 0.9rem !important;
        transition: color 0.3s;
    }
    
    .nav-links a:hover {
        color: #3b82f6;
    }
    
    /* ==================== HERO SECTION ==================== */
    .hero-section {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 30%, #1e3a8a 60%, #3b82f6 100%);
        background-size: 300% 300%;
        animation: gradientShift 15s ease infinite;
        padding: 5rem 3rem;
        border-radius: 30px;
        text-align: center;
        margin-bottom: 3rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }
    
    .hero-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        opacity: 0.5;
    }
    
    .hero-section::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
        animation: float 8s ease-in-out infinite;
    }
    
    .hero-content {
        position: relative;
        z-index: 2;
    }
    
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #e0e7ff;
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        font-size: 0.85rem !important;
        margin-bottom: 1.5rem;
        animation: fadeInDown 0.8s ease-out;
    }
    
    .hero-badge-dot {
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    .hero-title {
        font-size: 4rem !important;
        font-weight: 900;
        color: white;
        margin-bottom: 1rem;
        animation: fadeInUp 0.8s ease-out 0.2s both;
        text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    .hero-title-gradient {
        background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        background-size: 200% 200%;
        animation: gradientShift 5s ease infinite;
    }
    
    .hero-subtitle {
        font-size: 1.3rem !important;
        color: #cbd5e1;
        margin-bottom: 1rem;
        animation: fadeInUp 0.8s ease-out 0.4s both;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .hero-bangla {
        font-size: 1.6rem !important;
        color: #93c5fd;
        margin-bottom: 1rem;
        font-weight: 600;
        animation: fadeInUp 0.8s ease-out 0.6s both;
        font-family: 'Hind Siliguri', sans-serif !important;
    }
    
    .hero-bangla-sub {
        font-size: 1.1rem !important;
        color: #a5b4fc;
        animation: fadeInUp 0.8s ease-out 0.8s both;
        font-family: 'Hind Siliguri', sans-serif !important;
    }
    
    /* ==================== MODERN BUTTONS ==================== */
    .btn-primary {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white !important;
        padding: 1rem 2.5rem !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3) !important;
        position: relative;
        overflow: hidden;
    }
    
    .btn-primary::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }
    
    .btn-primary:hover::before {
        left: 100%;
    }
    
    .btn-primary:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 40px rgba(59, 130, 246, 0.4) !important;
    }
    
    .btn-secondary {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        color: white !important;
        padding: 1rem 2.5rem !important;
        border-radius: 50px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        cursor: pointer;
        transition: all 0.3s !important;
    }
    
    .btn-secondary:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-3px) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
    }
    
    /* ==================== SECTION STYLES ==================== */
    .section {
        padding: 4rem 2rem;
        margin-bottom: 2rem;
        animation: fadeInUp 0.8s ease-out;
    }
    
    .section-title {
        font-size: 2.5rem !important;
        font-weight: 800;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .section-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem !important;
        margin-bottom: 3rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* ==================== GLASSMORPHISM CARDS ==================== */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 24px;
        padding: 2rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .glass-card:hover::before {
        opacity: 1;
    }
    
    .glass-card:hover {
        transform: translateY(-8px) !important;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15) !important;
        border-color: rgba(59, 130, 246, 0.3);
    }
    
    /* ==================== FEATURE CARDS ==================== */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        text-align: center;
        margin-bottom: 1.5rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid #f1f5f9;
        position: relative;
        overflow: hidden;
    }
    
    .feature-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        transform: scaleX(0);
        transition: transform 0.4s;
    }
    
    .feature-card:hover::after {
        transform: scaleX(1);
    }
    
    .feature-card:hover {
        transform: translateY(-10px) !important;
        box-shadow: 0 25px 50px -12px rgba(59, 130, 246, 0.25) !important;
    }
    
    .feature-icon {
        font-size: 3rem !important;
        margin-bottom: 1rem;
        display: inline-block;
        animation: float 3s ease-in-out infinite;
    }
    
    .feature-title {
        font-size: 1.2rem !important;
        font-weight: 700;
        margin-bottom: 0.75rem;
        color: #1e293b;
    }
    
    .feature-desc {
        font-size: 0.9rem !important;
        color: #64748b;
        line-height: 1.6 !important;
    }
    
    /* ==================== STATS SECTION ==================== */
    .stats-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 3rem 2rem;
        border-radius: 30px;
        margin: 3rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .stats-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%233b82f6' fill-opacity='0.03' fill-rule='evenodd'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E");
    }
    
    .stat-card {
        text-align: center;
        padding: 1.5rem;
        position: relative;
        z-index: 1;
    }
    
    .stat-number {
        font-size: 3rem !important;
        font-weight: 900;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: #64748b;
        font-size: 0.9rem !important;
        font-weight: 500;
    }
    
    /* ==================== PROBLEM/SOLUTION ==================== */
    .problem-section {
        background: linear-gradient(135deg, #fef2f2, #fff1f2);
        padding: 2.5rem;
        border-radius: 24px;
        margin: 2rem 0;
        border: 1px solid #fecaca;
        position: relative;
        overflow: hidden;
        transition: all 0.3s;
    }
    
    .problem-section:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(239, 68, 68, 0.1);
    }
    
    .problem-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #ef4444, #f97316);
    }
    
    .solution-section {
        background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
        padding: 2.5rem;
        border-radius: 24px;
        margin: 2rem 0;
        border: 1px solid #bbf7d0;
        position: relative;
        overflow: hidden;
        transition: all 0.3s;
    }
    
    .solution-section:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(34, 197, 94, 0.1);
    }
    
    .solution-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #22c55e, #06b6d4);
    }
    
    /* ==================== PRICING CARDS ==================== */
    .pricing-card {
        background: white;
        padding: 2rem;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: 2px solid #f1f5f9;
        position: relative;
        overflow: hidden;
    }
    
    .pricing-card:hover {
        transform: translateY(-10px) !important;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15) !important;
    }
    
    .pricing-card.popular {
        border: 2px solid #3b82f6;
        background: linear-gradient(135deg, #eff6ff, #f5f3ff);
        transform: scale(1.05);
        animation: borderGlow 3s infinite;
    }
    
    .pricing-card.popular:hover {
        transform: scale(1.05) translateY(-10px) !important;
    }
    
    .popular-badge {
        position: absolute;
        top: -1px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
        padding: 0.4rem 1.5rem;
        border-radius: 0 0 12px 12px;
        font-size: 0.75rem !important;
        font-weight: 700;
        white-space: nowrap;
        letter-spacing: 0.5px;
    }
    
    .pricing-icon {
        font-size: 2.5rem !important;
        margin-bottom: 1rem;
    }
    
    .pricing-name {
        font-size: 1.3rem !important;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .pricing-price {
        font-size: 2.5rem !important;
        font-weight: 900;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 1rem 0;
    }
    
    .pricing-price span {
        font-size: 0.9rem !important;
        font-weight: 400;
        -webkit-text-fill-color: #64748b;
    }
    
    .pricing-features {
        text-align: left;
        margin: 1.5rem 0;
    }
    
    .pricing-features div {
        padding: 0.5rem 0;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.9rem !important;
        color: #475569;
    }
    
    .pricing-features div:last-child {
        border-bottom: none;
    }
    
    /* ==================== TESTIMONIAL CARDS ==================== */
    .testimonial-card {
        background: white;
        padding: 2rem;
        border-radius: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        height: 100%;
        transition: all 0.4s;
        border: 1px solid #f1f5f9;
        position: relative;
    }
    
    .testimonial-card::before {
        content: '"';
        position: absolute;
        top: 10px;
        left: 20px;
        font-size: 4rem !important;
        color: #3b82f6;
        opacity: 0.2;
        font-family: Georgia, serif;
    }
    
    .testimonial-card:hover {
        transform: translateY(-8px) !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1) !important;
    }
    
    .testimonial-stars {
        color: #fbbf24;
        font-size: 1.2rem !important;
        margin-bottom: 1rem;
    }
    
    .testimonial-text {
        font-style: italic;
        color: #475569;
        margin: 1rem 0;
        font-size: 0.95rem !important;
        line-height: 1.7 !important;
    }
    
    .testimonial-author {
        font-weight: 700;
        color: #1e293b;
        margin-top: 1rem;
    }
    
    .testimonial-role {
        font-size: 0.8rem !important;
        color: #94a3b8;
    }
    
    /* ==================== FAQ SECTION ==================== */
    .faq-item {
        background: white;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        border: 1px solid #f1f5f9;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .faq-item:hover {
        border-color: #3b82f6;
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.1);
        transform: translateX(5px);
    }
    
    .faq-question {
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.75rem;
        font-size: 1.05rem !important;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .faq-answer {
        color: #64748b;
        font-size: 0.95rem !important;
        padding-left: 1.5rem;
        border-left: 3px solid #3b82f6;
        line-height: 1.7 !important;
    }
    
    /* ==================== ROI CALCULATOR ==================== */
    .roi-calculator {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        padding: 3rem;
        border-radius: 30px;
        margin: 3rem 0;
        color: white;
        position: relative;
        overflow: hidden;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
    }
    
    .roi-calculator::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
        animation: float 10s ease-in-out infinite;
    }
    
    .roi-content {
        position: relative;
        z-index: 2;
    }
    
    .roi-box {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem;
        border-radius: 20px;
        margin-top: 1.5rem;
    }
    
    /* ==================== CTA SECTION ==================== */
    .cta-section {
        background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 50%, #3b82f6 100%);
        background-size: 200% 200%;
        animation: gradientShift 10s ease infinite;
        padding: 4rem 3rem;
        border-radius: 30px;
        text-align: center;
        margin-bottom: 3rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 25px 50px rgba(59, 130, 246, 0.3);
    }
    
    .cta-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }
    
    .cta-content {
        position: relative;
        z-index: 2;
    }
    
    /* ==================== TRUST BADGES ==================== */
    .trust-badge {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        border: 1px solid #f1f5f9;
        font-size: 0.8rem !important;
        color: #475569;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .trust-badge:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        border-color: #3b82f6;
    }
    
    /* ==================== DIVIDER ==================== */
    .modern-divider {
        margin: 4rem 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        position: relative;
    }
    
    .modern-divider::after {
        content: '◆';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 0 1rem;
        color: #3b82f6;
    }
    
    /* ==================== USER BADGES ==================== */
    .user-badge {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        padding: 1rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid #e2e8f0;
        transition: all 0.3s;
        font-weight: 500;
    }
    
    .user-badge:hover {
        transform: translateY(-5px);
        background: linear-gradient(135deg, #eff6ff, #f5f3ff);
        border-color: #3b82f6;
        box-shadow: 0 10px 20px rgba(59, 130, 246, 0.1);
    }
    
    /* ==================== DESCRIPTION BOX ==================== */
    .desc-box {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        padding: 3rem;
        border-radius: 30px;
        margin-bottom: 3rem;
        border: 1px solid #e2e8f0;
        position: relative;
        overflow: hidden;
    }
    
    .desc-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }
    
    .check-list {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1rem;
        margin-top: 2rem;
    }
    
    .check-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        transition: all 0.3s;
    }
    
    .check-item:hover {
        border-color: #3b82f6;
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(59, 130, 246, 0.1);
    }
    
    .check-icon {
        width: 24px;
        height: 24px;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.7rem !important;
        flex-shrink: 0;
    }
    
    /* ==================== RESPONSIVE ==================== */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2.5rem !important;
        }
        .hero-section {
            padding: 3rem 1.5rem;
        }
        .section {
            padding: 2rem 1rem;
        }
        .pricing-card.popular {
            transform: scale(1);
        }
    }
    
    /* ==================== ST BUTTON OVERRIDES ==================== */
    .stButton > button {
        border-radius: 50px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        padding: 0.75rem 2rem !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
    }
    

    /* ==================== EQUAL HEIGHT GRID FIX ==================== */
    .equal-height-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        align-items: stretch;
    }

    .equal-height-grid > div {
        display: flex;
        flex-direction: column;
    }

    .equal-height-grid .problem-section,
    .equal-height-grid .solution-section,
    .equal-height-grid .feature-card {
        flex: 1;
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    .equal-height-grid .problem-section > div,
    .equal-height-grid .solution-section > div,
    .equal-height-grid .feature-card > div {
        flex: 1;
    }

    /* 4-column grid */
    .equal-height-grid-4 {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        align-items: stretch;
    }

    .equal-height-grid-4 > div {
        display: flex;
        flex-direction: column;
    }

    .equal-height-grid-4 .feature-card {
        flex: 1;
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .equal-height-grid,
        .equal-height-grid-4 {
            grid-template-columns: 1fr;
        }
    }                
    /* Animation delays for staggered effects */
    .delay-1 { animation-delay: 0.1s; }
    .delay-2 { animation-delay: 0.2s; }
    .delay-3 { animation-delay: 0.3s; }
    .delay-4 { animation-delay: 0.4s; }
    .delay-5 { animation-delay: 0.5s; }
    .delay-6 { animation-delay: 0.6s; }
    </style>
    
    <!-- Animated Background -->
    <div class="animated-bg">
        <div class="floating-shape"></div>
        <div class="floating-shape"></div>
        <div class="floating-shape"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== NAVIGATION BAR ====================
    st.markdown("""
    <div class="navbar">
        <div class="nav-logo">🏗️ TenderAI (BD)</div>
        <div class="nav-links">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="#testimonials">Reviews</a>
            <a href="#faq">FAQ</a>
            <a href="#contact">Contact</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # # ==================== HERO SECTION ====================
    # st.markdown(f"""
    # <div class="hero-section">
    #     <div class="hero-content">
    #         <div class="hero-badge">
    #             <span class="hero-badge-dot"></span>
    #             🚀 AI-Powered • Bangladesh's First • PPR 2025 Compliant
    #         </div>
    #         <div class="hero-title">
    #             🏗️ <span class="hero-title-gradient">TenderAI (BD)</span>
    #         </div>
    #         <div class="hero-subtitle">AI Powered Tender Intelligence & Bid Optimization Platform</div>
    #         <div class="hero-bangla">বাংলাদেশের প্রথম AI-চালিত Tender Intelligence Platform</div>
    #         <div class="hero-bangla-sub">টেন্ডার বিশ্লেষণে পুরো দিন নয়, এখন লাগবে মাত্র কয়েক সেকেন্ড</div>
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)
    # ==================== EXTENSION DOWNLOAD SECTION ====================
    st.markdown("""
<style>
    .extension-hero {
        background: linear-gradient(135deg, #006A4E 0%, #F42A41 100%);
        border-radius: 24px;
        padding: 2rem;
        margin: 2rem 0;
        color: white;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .hero-content {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
    }
    .hero-badge {
        background: rgba(255,255,255,0.15);
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        display: inline-block;
        font-size: 0.85rem;
        backdrop-filter: blur(10px);
        align-self: flex-start;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .hero-badge-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #4CAF50;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
        100% { opacity: 1; transform: scale(1); }
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
    }
    .hero-title-gradient {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        font-weight: 500;
        opacity: 0.95;
        margin: 0;
    }
    .hero-bangla {
        font-size: 1.4rem;
        font-weight: 600;
        color: #FFD700;
        margin: 0.3rem 0;
    }
    .hero-bangla-sub {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 400;
        margin: 0;
    }
    .hero-egp-info {
        text-align: center;
        background: rgba(255,255,255,0.1);
        padding: 0.7rem;
        border-radius: 12px;
        margin: 0.3rem 0;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .hero-egp-info span {
        color: white;
        font-size: 0.95rem;
    }
    .hero-image {
        text-align: center;
        margin: 0.5rem 0;
    }
    .hero-image img {
        max-width: 180px;
        height: auto;
        background: white;
        border-radius: 12px;
        padding: 0.5rem 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .hero-description {
        color: rgba(255,255,255,0.95);
        text-align: center;
        font-size: 1.1rem;
        margin: 0.3rem 0;
    }
    .hero-compatibility {
        text-align: center;
        margin: 0.3rem 0;
    }
    .compatible-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        color: white;
        font-size: 0.75rem;
        margin: 0.2rem 0.3rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .hero-stats {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.15);
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .hero-stat-item {
        text-align: center;
        flex: 1;
        min-width: 80px;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #FFD700;
        display: block;
    }
    .stat-label {
        color: rgba(255,255,255,0.8);
        font-size: 0.85rem;
        display: block;
        margin-top: 0.2rem;
    }
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2rem;
        }
        .hero-stats {
            flex-direction: column;
        }
        .hero-badge {
            font-size: 0.75rem;
            padding: 0.3rem 0.8rem;
        }
    }
</style>

<div class="extension-hero">
    <div class="hero-content">
        <div class="hero-badge">
            <span class="hero-badge-dot"></span>
            🚀 AI-Powered • Bangladesh's First • PPR 2025 Compliant
        </div>
        
        <div class="hero-title">
            🏗️ <span class="hero-title-gradient">TenderAI (BD)</span>
        </div>
        
        <div class="hero-subtitle">
            AI Powered Tender Intelligence & Bid Optimization Platform
        </div>
        
        <div class="hero-bangla">
            বাংলাদেশের প্রথম AI-চালিত Tender Intelligence Platform
        </div>
        
        <div class="hero-bangla-sub">
            টেন্ডার বিশ্লেষণে পুরো দিন নয়, এখন লাগবে মাত্র কয়েক সেকেন্ড
        </div>
        
        <div class="hero-egp-info">
            <span>✅ e-GP Bangladesh ✓ LTM Tenders ✓ OTM Tenders Auto Fill Browser Extension</span>
        </div>
        
        <div class="hero-image">
            <img src="https://raw.githubusercontent.com/shomonrobie/iTender/main/assets/images/cptuEgpLogo.gif" alt="CPTU e-GP Logo" />
        </div>
        
        <p class="hero-description">
            Fill LTM/OTM tender forms instantly with your company data
        </p>
        
        <div class="hero-compatibility">
            <span class="compatible-badge">✓ Chrome</span>
            <span class="compatible-badge">✓ Edge</span>
            <span class="compatible-badge">✓ Opera</span>
            <span class="compatible-badge">✓ Brave</span>
        </div>
        
        <div class="hero-stats">
            <div class="hero-stat-item">
                <span class="stat-number">95%</span>
                <span class="stat-label">Time Saved</span>
            </div>
            <div class="hero-stat-item">
                <span class="stat-number">10,000+</span>
                <span class="stat-label">Forms Filled</span>
            </div>
            <div class="hero-stat-item">
                <span class="stat-number">40%</span>
                <span class="stat-label">Higher Win Rate</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    
    # # CTA Buttons
    # col1, col2, col3 = st.columns([1, 2, 1])
    # with col2:
    #     col_a, col_b = st.columns(2)
    #     with col_a:
    #         if st.button("🎥 ডেমো দেখুন", use_container_width=True, type="primary"):
    #             st.info("Demo video coming soon!")
    #     with col_b:
    #         if st.button("📞 ফ্রি কনসালটেশন বুক করুন", use_container_width=True):
    #             st.info("Call us: +880 1234 567890")
    
    # st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)



    # Streamlit button for navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Learn More About Extension", use_container_width=True, type="primary"):
            st.session_state.page = "extension_features"
            st.rerun()
    # Download button with login check
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📥 Download Extension for e-GP", use_container_width=True, type="primary", key="download_extension_btn"):
            if st.session_state.get('logged_in', False):
                st.session_state.page = "extension_download"
                st.rerun()
            else:
                st.session_state.show_login_prompt = True
                st.rerun()

    # Show login prompt using Streamlit components
    if st.session_state.get('show_login_prompt', False):
        st.markdown("---")
        
        # Create columns for centered prompt
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.container():
                st.markdown("""
                <div style="background: #fff3e0; border: 2px solid #ff9800; border-radius: 16px; padding: 1.5rem; text-align: center;">
                    <div style="font-size: 2rem;">🔐</div>
                    <h3 style="color: #e65100;">Login Required</h3>
                    <p style="color: #555;">Please login or register to download the extension</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("🔐 Login", use_container_width=True, type="primary", key="login_prompt_btn"):
                        st.session_state.page = "login"
                        st.session_state.show_login_prompt = False
                        st.rerun()
                
                with col_b:
                    if st.button("📝 Register", use_container_width=True, type="secondary", key="register_prompt_btn"):
                        st.session_state.page = "register"
                        st.session_state.show_login_prompt = False
                        st.rerun()
                
                with col_c:
                    if st.button("❌ Cancel", use_container_width=True, key="cancel_prompt_btn"):
                        st.session_state.show_login_prompt = False
                        st.rerun()
        
        st.markdown("---")
    
    render_workflow_section3()
    # ==================== STATS SECTION ====================
    st.markdown("""
    <div class="stats-container">
        <h2 class="section-title">📊 Trusted by Leading Organizations</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem;">
            <div class="stat-card">
                <div class="stat-number">95%</div>
                <div class="stat-label">Time Saved on Analysis</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">500+</div>
                <div class="stat-label">Tenders Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">35%</div>
                <div class="stat-label">Higher Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">24/7</div>
                <div class="stat-label">AI Availability</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== WHAT TenderAI (BD) DOES ====================
    st.markdown("""
    <div class="desc-box">
        <h2 class="section-title">✨ What is TenderAI (BD)?</h2>
        <p style="font-size: 1.15rem; text-align: center; color: #475569; max-width: 800px; margin: 0 auto;">
            <strong>TenderAI (BD)</strong> এমন একটি অত্যাধুনিক AI প্ল্যাটফর্ম যা টেন্ডার ডকুমেন্ট, BOQ এবং বাজার পরিস্থিতি বিশ্লেষণ করে 
            আপনাকে সবচেয়ে প্রতিযোগিতামূলক এবং লাভজনক বিডিং সিদ্ধান্ত নিতে সাহায্য করে।
        </p>
        <div class="check-list">
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>টেন্ডার বিশ্লেষণের সময় 95% পর্যন্ত কমান</span>
            </div>
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>বিড প্রস্তুতির খরচ কমান</span>
            </div>
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>আরও বেশি টেন্ডারে অংশগ্রহণ করুন</span>
            </div>
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>তথ্যভিত্তিক বিডিং সিদ্ধান্ত নিন</span>
            </div>
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>টেন্ডার জয়ের সম্ভাবনা বৃদ্ধি করুন</span>
            </div>
            <div class="check-item">
                <div class="check-icon">✓</div>
                <span>PPR 2025 সম্পূর্ণ compliant</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    
    # ==================== PROBLEM VS SOLUTION (FIXED) ====================
    st.markdown("""
    <div class="equal-height-grid">
        <div>
            <div class="problem-section">
                <h3 style="color: #dc2626; text-align: center; font-size: 1.3rem !important; margin-bottom: 1.5rem;">❌ এখনও কি আপনার টিম ঘণ্টার পর ঘণ্টা BOQ বিশ্লেষণ করে?</h3>
                <div style="margin-top: 1rem;">
                    <p style="color: #475569;">একটি বড় টেন্ডার বিশ্লেষণ করতে সাধারণত:</p>
                    <ul style="margin-top: 1rem; color: #64748b; line-height: 2;">
                        <li>👥 ৩-৫ জন কর্মী</li>
                        <li>⏰ ৪-৮ ঘণ্টা সময়</li>
                        <li>📊 অসংখ্য Excel Sheet</li>
                        <li>📋 শত শত BOQ Item</li>
                        <li>🧮 অসংখ্য Manual Calculation</li>
                    </ul>
                    <p style="margin-top: 1rem; padding: 1rem; background: rgba(239, 68, 68, 0.1); border-radius: 12px; color: #dc2626; font-weight: 600;">
                        <strong>তারপরও সঠিক বিড মূল্য নির্ধারণ করা কঠিন।</strong>
                    </p>
                </div>
            </div>
        </div>
        <div>
            <div class="solution-section">
                <h3 style="color: #16a34a; text-align: center; font-size: 1.3rem !important; margin-bottom: 1.5rem;">✨ TenderAI (BD) কী করে?</h3>
                <div style="margin-top: 1rem;">
                    <p style="color: #475569; font-weight: 600;">এক ক্লিকে:</p>
                    <ul style="margin-top: 1rem; color: #64748b; line-height: 2;">
                        <li>📋 টেন্ডার বিশ্লেষণ</li>
                        <li>📊 BOQ বিশ্লেষণ</li>
                        <li>🎯 Bid Optimization</li>
                        <li>👥 Competitor Simulation</li>
                        <li>⚠️ Risk Assessment</li>
                        <li>💰 Cost Analysis</li>
                        <li>📄 Executive Summary</li>
                    </ul>
                    <p style="margin-top: 1rem; padding: 1rem; background: rgba(34, 197, 94, 0.1); border-radius: 12px; color: #16a34a; font-weight: 600;">
                        <strong>সব কিছু কয়েক সেকেন্ডে! 🚀</strong>
                    </p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_all_counters()



    # ==================== KEY FEATURES ====================
    
    # Feature 1: AI Tender Analysis Engine
    st.markdown('<div id="features"></div>', unsafe_allow_html=True)
    st.markdown("""
    <h2 class="section-title">🤖 AI Tender Analysis Engine</h2>
    <p class="section-subtitle">কয়েক সেকেন্ডে সম্পূর্ণ টেন্ডার বিশ্লেষণ করুন AI দিয়ে</p>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">কয়েক সেকেন্ডে সম্পূর্ণ টেন্ডার বিশ্লেষণ</div>
            <ul style="margin-top: 0.5rem; padding-left: 1rem; color: #64748b;">
                <li>Eligibility Criteria Analysis</li>
                <li>Tender Requirement Extraction</li>
                <li>Mandatory Document Detection</li>
                <li>Risk Identification</li>
                <li>Technical Evaluation Summary</li>
                <li>Financial Requirement Summary</li>
                <li><strong style="color: #3b82f6;">Bid / No-Bid Recommendation</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card" style="text-align: left;">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">AI Tender Analysis System Features</div>
            <ul style="margin-top: 0.5rem; padding-left: 1rem; color: #64748b;">
                <li>📄 Automatic Document Parsing</li>
                <li>📊 Key Information Extraction</li>
                <li>⚠️ Risk & Compliance Check</li>
                <li>💡 Smart Recommendations</li>
                <li>📈 Market Comparison</li>
            </ul>
            <p style="margin-top: 1rem; font-size: 0.75rem; color: #94a3b8; background: #f8fafc; padding: 0.5rem; border-radius: 8px;"><strong>SEO:</strong> AI Tender Analysis Software Bangladesh, Tender Analysis System, eGP Tender Analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # Feature 2: Smart Bid Optimization Engine
    st.markdown("""
    <h2 class="section-title">🎯 Smart Bid Optimization Engine</h2>
    <p class="section-subtitle">কত টাকায় বিড করলে জয়ের সম্ভাবনা বেশি?</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    strategies = [
        ("⚔️", "Aggressive Bid Strategy", "সর্বোচ্চ প্রতিযোগিতামূলক বিড"),
        ("⚖️", "Moderate Bid Strategy", "ঝুঁকি ও লাভের ভারসাম্যপূর্ণ বিড"),
        ("🛡️", "Conservative Bid Strategy", "নিরাপদ ও উচ্চ লাভের বিড"),
        ("🎯", "Weighted Average", "AI-ভিত্তিক সুপারিশকৃত বিড মূল্য")
    ]
    
    for idx, (icon, title, desc) in enumerate(strategies):
        col = [col1, col2, col3, col4][idx]
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ==================== Competitor Simulation & Bid Optimization (FIXED) ====================
    st.markdown("""
    <div class="equal-height-grid">
        <div>
            <div class="feature-card">
                <div class="feature-icon">👥</div>
                <div class="feature-title">Competitor Simulation</div>
                <div class="feature-desc">বিভিন্ন সংখ্যক প্রতিযোগী ধরে সম্ভাব্য ফলাফল বিশ্লেষণ</div>
                <div style="margin-top: auto; padding-top: 1rem;">
                    <div style="padding: 0.75rem; background: #f8fafc; border-radius: 8px; font-size: 0.8rem !important; color: #64748b;">
                        <strong>Simulate:</strong> 3, 5, 10, 20+ competitors
                    </div>
                </div>
            </div>
        </div>
        <div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Bid Optimization Results</div>
                <div class="feature-desc">Three-Tier Analysis: Basic, Advanced (PPR 2025), Enhanced (ML)</div>
                <div style="margin-top: auto; padding-top: 1rem;">
                    <div style="padding: 0.75rem; background: #f8fafc; border-radius: 8px; font-size: 0.8rem !important; color: #64748b;">
                        <strong>Output:</strong> Recommended bid price with confidence score
                    </div>
                    <p style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8; background: #f8fafc; padding: 0.5rem; border-radius: 8px;"><strong>SEO:</strong> Bid Optimization Software, Tender Bid Calculator</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # Feature 3: BOQ Intelligence Platform
    st.markdown("""
    <h2 class="section-title">📊 BOQ Intelligence Platform</h2>
    <p class="section-subtitle">হাজার হাজার BOQ Item বিশ্লেষণ করুন মুহূর্তেই</p>
    """, unsafe_allow_html=True)
    
    # ==================== BOQ Processing & Analysis (FIXED) ====================
    st.markdown("""
    <div class="equal-height-grid">
        <div>
            <div class="feature-card">
                <div class="feature-icon">📄</div>
                <div class="feature-title">BOQ Processing</div>
                <ul style="margin-top: 0.5rem; padding-left: 1rem; color: #64748b;">
                    <li>📄 BOQ Upload (Excel/PDF)</li>
                    <li>🤖 Automated Item Analysis</li>
                    <li>✅ Quantity Verification</li>
                    <li>💰 Rate Comparison</li>
                </ul>
                <div style="margin-top: auto; padding-top: 1rem;">
                    <div style="padding: 0.75rem; background: linear-gradient(135deg, #eff6ff, #f5f3ff); border-radius: 8px; font-size: 0.8rem !important; color: #1e3a8a; border: 1px solid #bfdbfe;">
                        <strong>⚡ Process 1000+ items in seconds</strong>
                    </div>
                </div>
            </div>
        </div>
        <div>
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-title">Analysis & Insights</div>
                <ul style="margin-top: 0.5rem; padding-left: 1rem; color: #64748b;">
                    <li>📊 Cost Breakdown</li>
                    <li>📈 Margin Analysis</li>
                    <li>⚠️ Abnormal Item Detection</li>
                </ul>
                <div style="margin-top: auto; padding-top: 1rem;">
                    <div style="padding: 0.75rem; background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border-radius: 8px; font-size: 0.8rem !important; color: #16a34a; border: 1px solid #bbf7d0;">
                        <strong>🎯 AI-powered anomaly detection</strong>
                    </div>
                    <p style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8; background: #f8fafc; padding: 0.5rem; border-radius: 8px;"><strong>SEO:</strong> BOQ Analysis Software Bangladesh</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # Feature 4: Tender Management System
    st.markdown("""
    <h2 class="section-title">📋 Tender Management System</h2>
    <p class="section-subtitle">সব টেন্ডার এক প্ল্যাটফর্মে</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("📌", "Tender Tracking"),
        ("⏰", "Submission Reminder"),
        ("🔄", "Workflow Management"),
        ("👥", "Team Collaboration"),
        ("✅", "Approval Process"),
        ("📁", "Document Repository"),
        ("📊", "Audit Trail")
    ]
    
    for idx, (icon, label) in enumerate(features):
        col = [col1, col2, col3, col4][idx % 4]
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<p style="text-align: center; font-size: 0.8rem; color: #94a3b8; margin-top: 1rem;"><strong>SEO:</strong> Tender Management Software Bangladesh, eGP Management System</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    # Feature 5: Competitive Simulator (NEW - Premium Feature)
    st.markdown("""
    <h2 class="section-title">🏆 Competitive Simulator</h2>
    <p class="section-subtitle">বিভিন্ন প্রতিযোগী পরিস্থিতিতে আপনার জয়ের সম্ভাবনা বিশ্লেষণ করুন</p>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="equal-height-grid">
        <div>
            <div class="feature-card" style="text-align: left; height: 100%;">
                <div class="feature-icon">🎲</div>
                <div class="feature-title">Multi-Scenario Simulation</div>
                <div class="feature-desc">৫ থেকে ১৯ জন প্রতিযোগী - বিভিন্ন সংখ্যক প্রতিযোগী ধরে বিড বিশ্লেষণ</div>
                <ul style="margin-top: 1rem; padding-left: 1rem; color: #64748b;">
                    <li>📊 9+ different competitor scenarios</li>
                    <li>🎯 AI-powered optimal bid calculation</li>
                    <li>📈 Win probability for each scenario</li>
                    <li>💰 Expected profit analysis</li>
                    <li>⚠️ SLT threshold compliance (PPR 2025)</li>
                </ul>
                <div style="margin-top: 1rem; padding: 0.75rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white; text-align: center;">
                    <strong>✨ Professional & Enterprise Plans</strong>
                </div>
            </div>
        </div>
        <div>
            <div class="feature-card" style="text-align: left; height: 100%;">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">AI Recommendation Strategies</div>
                <div class="feature-desc">৫টি ভিন্ন AI স্ট্র্যাটেজি থেকে বেছে নিন</div>
                <ul style="margin-top: 1rem; padding-left: 1rem; color: #64748b;">
                    <li>🎯 <strong>Weighted Ensemble</strong> - Balanced approach (Recommended)</li>
                    <li>⚡ <strong>Aggressive</strong> - Highest win chance, lower profit</li>
                    <li>🛡️ <strong>Conservative</strong> - Highest profit, lower win chance</li>
                    <li>📊 <strong>Statistical</strong> - Mean - 0.5*Std deviation</li>
                    <li>🤖 <strong>ML-Style</strong> - Regression-based prediction</li>
                </ul>
                <div style="margin-top: 1rem; padding: 0.75rem; background: #f0fdf4; border-radius: 8px; color: #16a34a; text-align: center; font-size: 0.85rem;">
                    <strong>📥 Export Reports: HTML, CSV, Excel, JSON</strong>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Competitive Benefits Section
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                    border-radius: 20px; padding: 2rem; margin: 2rem 0; color: white; text-align: center;">
            <h3 style="color: white; font-size: 1.8rem; margin-bottom: 1rem;">📊 Real Impact of Competitive Simulator</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; margin-top: 1.5rem;">
                <div>
                    <div style="font-size: 2.5rem; font-weight: 800;">73%</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">Average Win Rate Increase</div>
                </div>
                <div>
                    <div style="font-size: 2.5rem; font-weight: 800;">181%</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">Higher Profit Margins</div>
                </div>
                <div>
                    <div style="font-size: 2.5rem; font-weight: 800;">108%</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">More Tenders Won</div>
                </div>
            </div>
            <p style="margin-top: 1.5rem; font-size: 0.9rem; opacity: 0.9;">
                *Based on user data from 50+ construction companies in Bangladesh
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    # Feature 5: Executive Dashboard
    st.markdown("""
    <h2 class="section-title">📊 Executive Dashboard</h2>
    <p class="section-subtitle">ব্যবসায়িক সিদ্ধান্ত এখন হবে তথ্যভিত্তিক</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    dashboard_features = [
        ("🏆", "Win Rate Analysis"),
        ("📈", "Tender Performance Analytics"),
        ("💰", "Revenue Forecasting"),
        ("📋", "Project Pipeline Tracking"),
        ("⚠️", "Risk Dashboard"),
        ("💡", "Profitability Insights")
    ]
    
    for idx, (icon, label) in enumerate(dashboard_features):
        col = [col1, col2, col3][idx % 3]
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # ==================== WHO IS USING ====================
    st.markdown("""
    <h2 class="section-title">👥 কারা ব্যবহার করছেন?</h2>
    <p class="section-subtitle">বাংলাদেশের শীর্ষস্থানীয় প্রতিষ্ঠানগুলো TenderAI (BD) ব্যবহার করছে</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    users = [
        "🏗️ Construction Companies",
        "📋 Contractors",
        "📦 Suppliers",
        "🔧 Engineering Firms",
        "🏭 EPC Contractors",
        "📊 Government Consultants",
        "🏗️ Infrastructure Developers",
        "📋 Procurement Teams"
    ]
    
    for idx, user in enumerate(users):
        col = [col1, col2, col3, col4][idx % 4]
        with col:
            st.markdown(f"""
            <div class="user-badge">{user}</div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # ==================== ROI CALCULATOR ====================
    st.markdown("""
    <div class="roi-calculator">
        <div class="roi-content">
            <h3 style="color: white; text-align: center; font-size: 2rem !important; margin-bottom: 0.5rem;">💰 ROI Calculator</h3>
            <p style="text-align: center; color: #a5b4fc; margin-bottom: 1.5rem; font-size: 1.1rem !important;">আপনার প্রতিষ্ঠান বছরে কত সাশ্রয় করতে পারে?</p>
            <div class="roi-box">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; text-align: center;">
                    <div>
                        <div style="font-size: 2rem !important; font-weight: 800; color: #60a5fa;">4</div>
                        <div style="color: #94a3b8; font-size: 0.85rem !important;">কর্মী</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem !important; font-weight: 800; color: #a78bfa;">4 hrs</div>
                        <div style="color: #94a3b8; font-size: 0.85rem !important;">প্রতিদিন</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem !important; font-weight: 800; color: #f472b6;">20</div>
                        <div style="color: #94a3b8; font-size: 0.85rem !important;">টেন্ডার/মাস</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 2rem; padding: 1.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 16px; border: 1px solid rgba(59, 130, 246, 0.3);">
                    <p style="color: #e0e7ff; font-size: 1.1rem !important;">বছরে <strong style="color: #60a5fa; font-size: 1.5rem !important;">শত শত</strong> মানব-ঘণ্টা সাশ্রয় সম্ভব</p>
                    <p style="color: #a5b4fc; margin-top: 0.5rem; font-size: 0.95rem !important;">TenderAI (BD) আপনার টিমকে কম সময়ে আরও বেশি টেন্ডার বিশ্লেষণের সুযোগ দেয়।</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # ==================== PRICING SECTION ====================
    st.markdown('<div id="pricing"></div>', unsafe_allow_html=True)
    st.markdown("""
    <h2 class="section-title">💰 Simple, Transparent Pricing</h2>
    <p class="section-subtitle">আপনার ব্যবসার জন্য সেরা প্ল্যান বেছে নিন</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <div class="pricing-icon">🆓</div>
            <div class="pricing-name">Free</div>
            <div class="pricing-price">৳0<span>/mo</span></div>
            <div class="pricing-features">
                <div>✅ 5 analyses/mo</div>
                <div>✅ Basic reports</div>
                <div>✅ Email support</div>
                <div>✅ 7-day history</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Free", key="plan_free", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="pricing-card">
            <div class="pricing-icon">📊</div>
            <div class="pricing-name">Basic</div>
            <div class="pricing-price">৳4,999<span>/mo</span></div>
            <div class="pricing-features">
                <div>✅ 30 analyses/mo</div>
                <div>✅ AI predictions</div>
                <div>✅ Export reports</div>
                <div>✅ Priority support</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Basic", key="plan_basic", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="pricing-card popular">
            <div class="popular-badge">🔥 Most Popular</div>
            <div class="pricing-icon">🚀</div>
            <div class="pricing-name">Professional</div>
            <div class="pricing-price">৳14,999<span>/mo</span></div>
            <div class="pricing-features">
                <div>✅ Unlimited analyses</div>
                <div>✅ ML predictions</div>
                <div>✅ Team collaboration</div>
                <div>✅ Priority support</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Professional", key="plan_pro", use_container_width=True, type="primary"):
            st.session_state.page = "register"
            st.rerun()
    
    with col4:
        st.markdown("""
        <div class="pricing-card">
            <div class="pricing-icon">🏢</div>
            <div class="pricing-name">Enterprise</div>
            <div class="pricing-price">৳49,999<span>/mo</span></div>
            <div class="pricing-features">
                <div>✅ Everything in Pro</div>
                <div>✅ Custom AI model</div>
                <div>✅ Dedicated support</div>
                <div>✅ SLA guarantee</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Enterprise", key="plan_enterprise", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # ==================== TESTIMONIALS ====================
    st.markdown('<div id="testimonials"></div>', unsafe_allow_html=True)
    st.markdown("""
    <h2 class="section-title">💬 What Our Users Say</h2>
    <p class="section-subtitle">আমাদের ব্যবহারকারীদের অভিজ্ঞতা</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="testimonial-card">
            <div class="testimonial-stars">⭐⭐⭐⭐⭐</div>
            <p class="testimonial-text">"TenderAI helped us increase our win rate by 35% in just 3 months! The AI analysis is incredibly accurate."</p>
            <div class="testimonial-author">Md. Rahman</div>
            <div class="testimonial-role">CEO, ABC Construction</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="testimonial-card">
            <div class="testimonial-stars">⭐⭐⭐⭐⭐</div>
            <p class="testimonial-text">"The AI predictions are remarkably accurate. Saved us from many bad bids. A must-have for any contractor."</p>
            <div class="testimonial-author">Ms. Khan</div>
            <div class="testimonial-role">Procurement Manager</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="testimonial-card">
            <div class="testimonial-stars">⭐⭐⭐⭐⭐</div>
            <p class="testimonial-text">"PPR 2025 compliance checker is a lifesaver. The BOQ analysis saves us days of manual work."</p>
            <div class="testimonial-author">Eng. Islam</div>
            <div class="testimonial-role">Project Director</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)
    
    # ==================== FAQ SECTION (UPDATED with Competitive) ====================
    st.markdown('<div id="faq"></div>', unsafe_allow_html=True)
    st.markdown("""
    <h2 class="section-title">❓ Frequently Asked Questions</h2>
    <p class="section-subtitle">আপনার জিজ্ঞাসার উত্তর</p>
    """, unsafe_allow_html=True)

    faqs = [
        {
            "question_en": "What is Competitive Simulator?",
            "question_bn": "Competitive  সিমুলেটর কী?",
            "answer_en": "The Competitive Simulator is an AI-powered tool that analyzes multiple competitor scenarios (5 to 19 competitors) and recommends the optimal bid price that balances win probability and profit margin. It simulates best-case, expected, and worst-case competition scenarios to give you data-driven bidding decisions.",
            "answer_bn": "Competitive  সিমুলেটর একটি AI-চালিত টুল যা বিভিন্ন প্রতিযোগী পরিস্থিতি (৫ থেকে ১৯ জন প্রতিযোগী) বিশ্লেষণ করে এবং সর্বোত্তম বিড মূল্য সুপারিশ করে যা জয়ের সম্ভাবনা ও মুনাফার মধ্যে ভারসাম্য রাখে। এটি সেরা, প্রত্যাশিত এবং সবচেয়ে খারাপ প্রতিযোগিতা পরিস্থিতি সিমুলেট করে তথ্যভিত্তিক বিডিং সিদ্ধান্ত দেয়।"
        },
        {
            "question_en": "How accurate is the win probability calculation?",
            "question_bn": "জয়ের সম্ভাবনার হিসাব কতটা নির্ভুল?",
            "answer_en": "The win probability is calculated using normal distribution model based on competitor bid patterns, historical data, and PPR 2025 formulas. Users report accuracy within ±10% of actual results. The more data you provide, the more accurate it becomes.",
            "answer_bn": "জয়ের সম্ভাবনা নর্মাল ডিস্ট্রিবিউশন মডেল ব্যবহার করে গণনা করা হয় যা প্রতিযোগীদের দরের ধরণ, ঐতিহাসিক তথ্য এবং পিপিআর ২০২৫ সূত্রের উপর ভিত্তি করে। ব্যবহারকারীরা জানিয়েছেন যে প্রকৃত ফলাফলের সাথে ±১০% এর মধ্যে নির্ভুলতা থাকে। আপনি যত বেশি তথ্য দেবেন, এটি তত নির্ভুল হবে।"
        },
        {
            "question_en": "What AI strategies are available?",
            "question_bn": "কি কি AI স্ট্র্যাটেজি উপলব্ধ?",
            "answer_en": "Five strategies: Weighted Ensemble (balanced - recommended), Aggressive (highest win chance), Conservative (highest profit), Statistical (mean - 0.5*std), and ML-Style (regression-based prediction). Each strategy suits different business goals.",
            "answer_bn": "পাঁচটি স্ট্র্যাটেজি: ওয়েটেড এনসেম্বল (ভারসাম্যপূর্ণ - সুপারিশকৃত), এগ্রেসিভ (সর্বোচ্চ জয়ের সম্ভাবনা), কনজারভেটিভ (সর্বোচ্চ মুনাফা), স্ট্যাটিস্টিক্যাল (গড় - ০.৫*স্ট্যান্ডার্ড ডেভিয়েশন), এবং এমএল-স্টাইল (রিগ্রেশন-ভিত্তিক পূর্বাভাস)। প্রতিটি স্ট্র্যাটেজি বিভিন্ন ব্যবসায়িক লক্ষ্যের জন্য উপযুক্ত।"
        },
        {
            "question_en": "What is SLT and how does your system handle it?",
            "question_bn": "SLT কী এবং আপনার সিস্টেম এটি কিভাবে হ্যান্ডেল করে?",
            "answer_en": "SLT (Substantially Lower Tender) is a PPR 2025 threshold below which bids are automatically rejected. Our system automatically calculates the SLT threshold based on competitor bids and ensures your recommended bid stays safely above it, preventing automatic disqualification.",
            "answer_bn": "SLT (সাবস্ট্যান্টিয়ালি লোয়ার টেন্ডার) হল পিপিআর ২০২৫-এর একটি সীমা যার নিচে বিড স্বয়ংক্রিয়ভাবে বাতিল হয়ে যায়। আমাদের সিস্টেম প্রতিযোগীদের দরের ভিত্তিতে স্বয়ংক্রিয়ভাবে SLT সীমা গণনা করে এবং নিশ্চিত করে যে আপনার প্রস্তাবিত বিড নিরাপদে এর উপরে থাকে, যা স্বয়ংক্রিয় অযোগ্যতা প্রতিরোধ করে।"
        },
        {
            "question_en": "Can I export reports?",
            "question_bn": "আমি কি রিপোর্ট এক্সপোর্ট করতে পারব?",
            "answer_en": "Yes! Professional and Enterprise plans support exporting reports in HTML, CSV, Excel, and JSON formats. The HTML report includes all analysis details, competitor tables, calculation breakdowns, and financial projections.",
            "answer_bn": "হ্যাঁ! প্রফেশনাল এবং এন্টারপ্রাইজ প্ল্যানে HTML, CSV, Excel, এবং JSON ফরম্যাটে রিপোর্ট এক্সপোর্ট করা যায়। HTML রিপোর্টে সমস্ত বিশ্লেষণ বিবরণ, প্রতিযোগীদের টেবিল, গণনার বিবরণ এবং আর্থিক প্রজেকশন থাকে।"
        },
        {
            "question_en": "What's included in the Free plan?",
            "question_bn": "ফ্রি প্ল্যানে কি কি আছে?",
            "answer_en": "Free plan includes 5 BOQ generations, 5 bid optimizations, 5 tender analyses per month, and view-only rate access. Competitive Simulator and export features require Professional or Enterprise plan.",
            "answer_bn": "ফ্রি প্ল্যানে প্রতি মাসে ৫টি BOQ জেনারেশন, ৫টি বিড অপটিমাইজেশন, ৫টি টেন্ডার বিশ্লেষণ এবং ভিউ-অনলি রেট অ্যাক্সেস রয়েছে। Competitive  সিমুলেটর এবং এক্সপোর্ট ফিচারের জন্য প্রফেশনাল বা এন্টারপ্রাইজ প্ল্যান প্রয়োজন।"
        },
        {
            "question_en": "How does Competitive Simulator differ from basic bid optimization?",
            "question_bn": "Competitive  বেসিক বিড অপটিমাইজেশন থেকে কীভাবে আলাদা?",
            "answer_en": "Basic bid optimization gives a single recommended price based on simple averages. Competitive Simulator provides 9+ competitor scenarios, 5 AI strategies, detailed scenario breakdowns, exportable reports, and historical tracking - giving you a complete competitive intelligence system.",
            "answer_bn": "বেসিক বিড অপটিমাইজেশন শুধু একটি প্রস্তাবিত মূল্য দেয় সহজ গড়ের ভিত্তিতে। Competitive  সিমুলেটর দেয় ৯+ প্রতিযোগী পরিস্থিতি, ৫টি AI স্ট্র্যাটেজি, বিস্তারিত পরিস্থিতি বিশ্লেষণ, এক্সপোর্টযোগ্য রিপোর্ট এবং ঐতিহাসিক ট্র্যাকিং - যা আপনাকে একটি সম্পূর্ণ প্রতিযোগিতামূলক ইন্টেলিজেন্স সিস্টেম দেয়।"
        },
        {
            "question_en": "Is TenderAI compliant with Bangladesh PPR 2025?",
            "question_bn": "টেন্ডারএআই কি বাংলাদেশ পিপিআর ২০২৫-এর সাথে সঙ্গতিপূর্ণ?",
            "answer_en": "Yes! TenderAI is fully compliant with Bangladesh Public Procurement Rules 2025, including SLT threshold calculation, NPPI methodology, and weighted average formulas as defined in e-GP standard tender documents.",
            "answer_bn": "হ্যাঁ! টেন্ডারএআই বাংলাদেশ পাবলিক প্রকিউরমেন্ট রুলস ২০২৫-এর সাথে সম্পূর্ণ সঙ্গতিপূর্ণ, যার মধ্যে রয়েছে SLT থ্রেশহোল্ড গণনা, NPPI পদ্ধতি এবং e-GP স্ট্যান্ডার্ড টেন্ডার ডকুমেন্টে সংজ্ঞায়িত ওয়েটেড এভারেজ সূত্র।"
        }
    ]

    # Display FAQs in two columns
    for i in range(0, len(faqs), 2):
        col1, col2 = st.columns(2)
        
        with col1:
            faq = faqs[i]
            with st.expander(f"❓ {faq['question_en']} | {faq['question_bn']}"):
                st.markdown(f"**🇬🇧 English:** {faq['answer_en']}")
                st.markdown(f"**🇧🇩 বাংলা:** {faq['answer_bn']}")
        
        if i + 1 < len(faqs):
            with col2:
                faq = faqs[i + 1]
                with st.expander(f"❓ {faq['question_en']} | {faq['question_bn']}"):
                    st.markdown(f"**🇬🇧 English:** {faq['answer_en']}")
                    st.markdown(f"**🇧🇩 বাংলা:** {faq['answer_bn']}")

    st.markdown('<div class="modern-divider"></div>', unsafe_allow_html=True)

    
    # ==================== FINAL CTA ====================
    st.markdown('<div id="contact"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="cta-section">
        <div class="cta-content">
            <h2 style="color: white; font-size: 2.5rem !important; font-weight: 800; margin-bottom: 1rem;">Ready to Win More Tenders?</h2>
            <p style="color: #e0e7ff; margin-bottom: 2rem; font-size: 1.2rem !important;">আপনার টেন্ডার বিশ্লেষণকে নিয়ে যান AI-এর পরবর্তী পর্যায়ে</p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; max-width: 900px; margin: 0 auto 2rem auto;">
                <div style="color: white; background: rgba(255,255,255,0.1); padding: 0.75rem; border-radius: 12px; backdrop-filter: blur(10px);">✔ দ্রুত বিশ্লেষণ</div>
                <div style="color: white; background: rgba(255,255,255,0.1); padding: 0.75rem; border-radius: 12px; backdrop-filter: blur(10px);">✔ কম খরচ</div>
                <div style="color: white; background: rgba(255,255,255,0.1); padding: 0.75rem; border-radius: 12px; backdrop-filter: blur(10px);">✔ উন্নত সিদ্ধান্ত</div>
                <div style="color: white; background: rgba(255,255,255,0.1); padding: 0.75rem; border-radius: 12px; backdrop-filter: blur(10px);">✔ অধিক দক্ষতা</div>
                <div style="color: white; background: rgba(255,255,255,0.1); padding: 0.75rem; border-radius: 12px; backdrop-filter: blur(10px);">✔ জয়ের সম্ভাবনা বৃদ্ধি</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 আজই ডেমো বুক করুন", use_container_width=True, type="primary"):
            st.info("Please call us at +880 1234 567890 or email sales@itenderbd.com")
        st.markdown("""
        <div style="text-align: center; margin-top: 1rem; color: #64748b;">
            <p>📞 +880 1234 567890 | 📧 sales@itenderbd.com | 🌐 www.itenderbd.com</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Trust Badges
    st.markdown("---")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    badges = ["✓ PPR 2025", "✓ e-GP Ready", "✓ SSL Secure", "✓ 24/7 Support", "✓ BD Made", "✓ AI Powered"]
    for idx, badge in enumerate(badges):
        with [col1, col2, col3, col4, col5, col6][idx]:
            st.markdown(f"<div class='trust-badge'>{badge}</div>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #94a3b8; font-size: 0.85rem !important;">
        <p>© 2026 TenderAI (BD). All rights reserved. | Bangladesh's First AI-Powered Tender Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)