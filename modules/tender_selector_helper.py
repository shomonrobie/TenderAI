# modules/tender_selector_helper.py - FIXED three-level costs

import streamlit as st
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional
from modules.tender_selector import render_tender_selector, get_tenders_for_company
from modules.boq_generator import BOQGenerator

DB_PATH = "data/tender_system.db"

# modules/tender_selector_helper.py - FIXED three-level cost lookup

def get_three_level_costs_from_rate_book(boq_id: int, company_id: int) -> Dict[str, float]:
    """
    Get three-level costs (Aggressive, Competitive, Standard) from the rate book
    for the items in a BOQ.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # ✅ Get BOQ's rate book and version
    cursor.execute("""
        SELECT rate_book_id, version_id
        FROM boq_generation_history
        WHERE id = ?
    """, (boq_id,))
    
    boq = cursor.fetchone()
    
    if not boq or not boq['rate_book_id'] or not boq['version_id']:
        print(f"⚠️ No rate_book_id or version_id for BOQ {boq_id}")
        conn.close()
        return {'aggressive': 0, 'competitive': 0, 'standard': 0}
    
    rate_book_id = boq['rate_book_id']
    version_id = boq['version_id']
    
    print(f"🔍 Looking up three-level costs for BOQ {boq_id}")
    print(f"   Rate Book ID: {rate_book_id}, Version ID: {version_id}")
    
    # ✅ Get BOQ items
    cursor.execute("""
        SELECT item_code, quantity
        FROM boq_items
        WHERE boq_id = ?
    """, (boq_id,))
    
    items = cursor.fetchall()
    
    if not items:
        print(f"⚠️ No items found for BOQ {boq_id}")
        conn.close()
        return {'aggressive': 0, 'competitive': 0, 'standard': 0}
    
    print(f"   Found {len(items)} items")
    
    total_aggressive = 0
    total_competitive = 0
    total_standard = 0
    
    matched_count = 0
    
    for item in items:
        item_code = item['item_code']
        quantity = item['quantity'] or 0
        
        # ✅ First try: Use the exact rate_book_id and version_id
        cursor.execute("""
            SELECT pricing_level, price
            FROM tenant_pricing_levels
            WHERE rate_item_id IN (
                SELECT id FROM tenant_rate_items
                WHERE rate_book_id = ? AND item_code = ? AND is_active = 1
            )
            AND rate_version_id = ?
        """, (rate_book_id, item_code, version_id))
        
        pricing = cursor.fetchall()
        
        # ✅ If no results, try with ANY version of the rate book
        if not pricing:
            cursor.execute("""
                SELECT pricing_level, price
                FROM tenant_pricing_levels
                WHERE rate_item_id IN (
                    SELECT id FROM tenant_rate_items
                    WHERE rate_book_id = ? AND item_code = ? AND is_active = 1
                )
                AND rate_version_id IN (
                    SELECT id FROM tenant_rate_versions
                    WHERE rate_book_id = ? AND is_current = 1
                )
            """, (rate_book_id, item_code, rate_book_id))
            
            pricing = cursor.fetchall()
        
        # ✅ If still no results, try ANY active rate book for this company
        if not pricing:
            cursor.execute("""
                SELECT pricing_level, price
                FROM tenant_pricing_levels
                WHERE rate_item_id IN (
                    SELECT id FROM tenant_rate_items
                    WHERE item_code = ? AND is_active = 1
                )
                AND rate_version_id IN (
                    SELECT id FROM tenant_rate_versions
                    WHERE rate_book_id IN (
                        SELECT id FROM tenant_rate_books
                        WHERE tenant_id = ? AND is_active = 1 AND is_archived = 0
                    )
                    AND is_current = 1
                )
            """, (item_code, company_id))
            
            pricing = cursor.fetchall()
        
        aggressive_rate = 0
        competitive_rate = 0
        standard_rate = 0
        
        for p in pricing:
            level = p['pricing_level']
            price = p['price'] or 0
            if level == 'AGGRESSIVE':
                aggressive_rate = price
            elif level == 'COMPETITIVE':
                competitive_rate = price
            elif level == 'STANDARD':
                standard_rate = price
        
        if aggressive_rate > 0 or competitive_rate > 0 or standard_rate > 0:
            matched_count += 1
        
        # ✅ Debug: Print what we found
        print(f"   Item: {item_code} -> Agg: {aggressive_rate}, Comp: {competitive_rate}, Std: {standard_rate}")
        
        total_aggressive += quantity * aggressive_rate
        total_competitive += quantity * competitive_rate
        total_standard += quantity * standard_rate
    
    conn.close()
    
    print(f"📊 Three-level costs: Agg: {total_aggressive}, Comp: {total_competitive}, Std: {total_standard}")
    print(f"   Matched items: {matched_count}/{len(items)}")
    
    return {
        'aggressive': total_aggressive,
        'competitive': total_competitive,
        'standard': total_standard
    }


def get_boq_items_for_tender(tender_id: str, company_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch BOQ data for a tender - ONLY if it's a FINAL/LOCKED BOQ.
    """
    boq_gen = BOQGenerator()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # ✅ Get FINAL/LOCKED BOQ
    cursor.execute("""
        SELECT id, rate_book_id, version_id, rate_source, selected_zone, total_estimated_cost
        FROM boq_generation_history
        WHERE tender_id = ? AND company_id = ? AND is_locked = 1
        ORDER BY generated_at DESC
        LIMIT 1
    """, (tender_id, company_id))
    
    boq = cursor.fetchone()
    conn.close()
    
    if not boq:
        return None
    
    boq_id = boq['id']
    
    # ✅ Get BOQ items
    boq_data = boq_gen.get_boq_by_id(boq_id)
    
    if not boq_data:
        return None
    
    # ✅ Add rate book name
    if boq['rate_book_id']:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM tenant_rate_books WHERE id = ?
        """, (boq['rate_book_id'],))
        book = cursor.fetchone()
        conn.close()
        if book:
            boq_data['boq']['rate_book_name'] = book['name']
    
    # ✅ Get three-level costs
    three_level_costs = get_three_level_costs_from_rate_book(boq_id, company_id)
    boq_data['three_level_costs'] = three_level_costs
    
    return boq_data

def debug_rate_book_pricing(rate_book_id: int, version_id: int):
    """Debug function to check pricing levels in a rate book."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n🔍 Debugging Rate Book {rate_book_id}, Version {version_id}")
    
    cursor.execute("""
        SELECT DISTINCT pricing_level, COUNT(*) as count
        FROM tenant_pricing_levels
        WHERE rate_version_id = ?
        GROUP BY pricing_level
    """, (version_id,))
    
    levels = cursor.fetchall()
    print(f"   Pricing Levels in version: {[dict(l) for l in levels]}")
    
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM tenant_rate_items
        WHERE rate_book_id = ? AND is_active = 1
    """, (rate_book_id,))
    
    items = cursor.fetchone()
    print(f"   Active items in rate book: {items['count'] if items else 0}")
    
    conn.close()

def render_tender_selector_with_boq(db, company_id: int, include_manual_entry: bool = True) -> Optional[Dict[str, Any]]:
    """
    Render tender selector and fetch FINAL/LOCKED BOQ data directly.
    """
    selected_tender_id, tender_title, official_estimate, procurement_type, \
    procuring_entity, division, district = render_tender_selector(
        db=db,
        company_id=company_id,
        search_term="",
        include_manual_entry=include_manual_entry,
        title="📋 Select Tender for Bid Analysis",
        show_table=True,
        show_summary=True
    )
    
    if not selected_tender_id and not tender_title:
        return None
    
    if selected_tender_id is None:
        return {
            'tender_id': None,
            'tender_title': tender_title,
            'official_estimate': official_estimate,
            'procurement_type': procurement_type,
            'procuring_entity': procuring_entity,
            'division': division,
            'district': district,
            'boq_data': None,
            'boq_status': 'manual_entry'
        }
    
    # ✅ Get BOQ data using BOQGenerator
    boq_data = get_boq_items_for_tender(selected_tender_id, company_id)
    
    if boq_data is None:
        return {
            'tender_id': selected_tender_id,
            'tender_title': tender_title,
            'official_estimate': official_estimate,
            'procurement_type': procurement_type,
            'procuring_entity': procuring_entity,
            'division': division,
            'district': district,
            'boq_data': None,
            'boq_status': 'not_found',
            'boq_message': 'No locked BOQ found for this tender.'
        }
    
    # ✅ Extract data from boq_data
    boq = boq_data.get('boq', {})
    items = boq_data.get('items', [])
    three_level_costs = boq_data.get('three_level_costs', {})
    
    return {
        'tender_id': selected_tender_id,
        'tender_title': tender_title,
        'official_estimate': official_estimate,
        'procurement_type': procurement_type,
        'procuring_entity': procuring_entity,
        'division': division,
        'district': district,
        'boq_data': boq_data,
        'boq_status': 'locked',
        'boq_id': boq.get('id'),
        'total_estimated_cost': boq.get('total_estimated_cost', 0),
        'item_count': boq.get('item_count', 0),
        'items': items,
        'rate_source': boq.get('rate_source', ''),
        'selected_zone': boq.get('selected_zone', ''),
        'rate_book_name': boq.get('rate_book_name', ''),
        'three_level_costs': three_level_costs
    }