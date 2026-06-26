# modules/subscription_plans.py
"""
Subscription Plans - Loaded from database with fallback defaults
"""

import streamlit as st
from typing import Dict, List, Optional
from database.unified_db_manager import db
from datetime import datetime, timedelta

# Default plans (used only for initialization)
DEFAULT_PLANS = [
    {
        'plan_name': 'free',
        'plan_type': 'company',
        'monthly_price': 0,
        'yearly_price': 0,
        'max_boq_generations': 5,
        'max_bid_optimizations': 5,
        'max_tender_analyses': 5,
        'max_users': 1,
        'extension_auto_fills': 5,
        'can_export_data': False,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_manage_team': False,
        'description': 'Free plan with basic features',
        'color': '#6c757d',
        'badge': '🆓',
        'features': [
            '5 analyses/month',
            'Basic Bid Optimizer',
            'Rate Viewer',
            'Basic reports',
            'Email support',
            '7-day history'
        ]
    },
    {
        'plan_name': 'basic',
        'plan_type': 'company',
        'monthly_price': 4999,
        'yearly_price': 49990,
        'max_boq_generations': 30,
        'max_bid_optimizations': 30,
        'max_tender_analyses': 30,
        'max_users': 3,
        'extension_auto_fills': 30,
        'can_export_data': True,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_manage_team': False,
        'description': 'Basic plan for small businesses',
        'color': '#3b82f6',
        'badge': '📊',
        'features': [
            '30 analyses/month',
            'Basic Bid Optimizer',
            'Advanced Bid Optimizer',
            'AI predictions',
            'Export reports',
            '30-day history',
            'Email support'
        ]
    },
    {
        'plan_name': 'professional',
        'plan_type': 'company',
        'monthly_price': 14999,
        'yearly_price': 149990,
        'max_boq_generations': 100,
        'max_bid_optimizations': 100,
        'max_tender_analyses': -1,
        'max_users': 10,
        'extension_auto_fills': 100,
        'can_export_data': True,
        'can_edit_rates': True,
        'can_delete_rates': False,
        'can_create_versions': True,
        'can_manage_team': True,
        'description': 'Professional plan for growing businesses',
        'color': '#8b5cf6',
        'badge': '⭐',
        'features': [
            'Unlimited analyses',
            'Competitive Bid Simulator',
            'ML predictions',
            'Competitor tracking',
            'Team collaboration',
            'Priority support',
            'API access'
        ]
    },
    {
        'plan_name': 'enterprise',
        'plan_type': 'company',
        'monthly_price': 49999,
        'yearly_price': 499990,
        'max_boq_generations': -1,
        'max_bid_optimizations': -1,
        'max_tender_analyses': -1,
        'max_users': -1,
        'extension_auto_fills': -1,
        'can_export_data': True,
        'can_edit_rates': True,
        'can_delete_rates': True,
        'can_create_versions': True,
        'can_manage_team': True,
        'description': 'Enterprise plan for large organizations',
        'color': '#10b981',
        'badge': '👑',
        'features': [
            'Everything in Professional',
            'Custom AI model',
            'Dedicated support',
            'SLA guarantee',
            'On-premise option'
        ]
    }
]


# Cache for plans
_plans_cache = None
_plans_cache_time = None


def ensure_default_plans():
    """Ensure default plans exist in the database"""
    try:
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            
            # Check if any plans exist
            cursor.execute("SELECT COUNT(*) FROM subscription_plans")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("📊 Inserting default subscription plans...")
                for plan in DEFAULT_PLANS:
                    cursor.execute("""
                        INSERT INTO subscription_plans (
                            plan_name, plan_type, monthly_price, yearly_price,
                            max_boq_generations, max_bid_optimizations, max_tender_analyses,
                            max_users, extension_auto_fills,
                            can_export_data, can_edit_rates, can_delete_rates,
                            can_create_versions, can_manage_team, description
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        plan['plan_name'],
                        plan['plan_type'],
                        plan['monthly_price'],
                        plan['yearly_price'],
                        plan['max_boq_generations'],
                        plan['max_bid_optimizations'],
                        plan['max_tender_analyses'],
                        plan['max_users'],
                        plan['extension_auto_fills'],
                        1 if plan['can_export_data'] else 0,
                        1 if plan['can_edit_rates'] else 0,
                        1 if plan['can_delete_rates'] else 0,
                        1 if plan['can_create_versions'] else 0,
                        1 if plan['can_manage_team'] else 0,
                        plan['description']
                    ))
                conn.commit()
                print(f"✅ Inserted {len(DEFAULT_PLANS)} default plans")
                return True
            else:
                print(f"📊 {count} plans already exist in database")
                return True
                
    except Exception as e:
        print(f"⚠️ Error ensuring default plans: {e}")
        return False


def get_plans_from_db(force_refresh: bool = False) -> Dict[str, Dict]:
    """
    Load plans from subscription_plans table
    
    Args:
        force_refresh: Force refresh from database
    
    Returns:
        Dict of plan configurations
    """
    global _plans_cache, _plans_cache_time
    
    # Return cached plans if not expired (5 minutes)
    if not force_refresh and _plans_cache is not None:
        
        if _plans_cache_time and datetime.now() - _plans_cache_time < timedelta(minutes=5):
            return _plans_cache
    
    try:
        # Ensure plans exist first
        ensure_default_plans()
        
        with db.get_connection() as conn:
            cursor = db.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT 
                    plan_name,
                    monthly_price,
                    yearly_price,
                    max_boq_generations,
                    max_bid_optimizations,
                    max_tender_analyses,
                    max_users,
                    extension_auto_fills,
                    can_export_data,
                    can_edit_rates,
                    can_delete_rates,
                    can_create_versions,
                    can_manage_team,
                    description,
                    is_active
                FROM subscription_plans
                WHERE is_active = 1
                ORDER BY monthly_price
            """)
            
            rows = cursor.fetchall()
            
            plans = {}
            for row in rows:
                plan_name = row['plan_name']
                plans[plan_name] = {
                    'name': plan_name.title(),
                    'price_monthly': row['monthly_price'] or 0,
                    'price_yearly': row['yearly_price'] or 0,
                    'analyses_limit': row['max_tender_analyses'] or 5,
                    'max_boq_generations': row['max_boq_generations'] or 5,
                    'max_bid_optimizations': row['max_bid_optimizations'] or 5,
                    'extension_auto_fills': row['extension_auto_fills'] or 5,
                    'users_limit': row['max_users'] or 1,
                    'can_export_data': bool(row['can_export_data']),
                    'can_edit_rates': bool(row['can_edit_rates']),
                    'can_delete_rates': bool(row['can_delete_rates']),
                    'can_create_versions': bool(row['can_create_versions']),
                    'can_manage_team': bool(row['can_manage_team']),
                    'description': row['description'] or '',
                    'is_active': bool(row['is_active']),
                    'color': _get_plan_color(plan_name),
                    'badge': _get_plan_badge(plan_name),
                    'features': _get_plan_features(plan_name)
                }
            
            _plans_cache = plans
            _plans_cache_time = datetime.now()
            
            print(f"📊 Loaded {len(plans)} plans from database")
            return plans
            
    except Exception as e:
        print(f"⚠️ Error loading plans from database: {e}")
        # Fallback to default plans
        return get_default_plans_dict()


def get_default_plans_dict() -> Dict[str, Dict]:
    """Convert DEFAULT_PLANS list to dict format"""
    plans = {}
    for plan in DEFAULT_PLANS:
        plan_name = plan['plan_name']
        plans[plan_name] = {
            'name': plan_name.title(),
            'price_monthly': plan['monthly_price'],
            'price_yearly': plan['yearly_price'],
            'analyses_limit': plan['max_tender_analyses'],
            'max_boq_generations': plan['max_boq_generations'],
            'max_bid_optimizations': plan['max_bid_optimizations'],
            'extension_auto_fills': plan['extension_auto_fills'],
            'users_limit': plan['max_users'],
            'can_export_data': plan['can_export_data'],
            'can_edit_rates': plan['can_edit_rates'],
            'can_delete_rates': plan['can_delete_rates'],
            'can_create_versions': plan['can_create_versions'],
            'can_manage_team': plan['can_manage_team'],
            'description': plan['description'],
            'is_active': True,
            'color': plan.get('color', '#6c757d'),
            'badge': plan.get('badge', '📋'),
            'features': plan.get('features', ['Basic features'])
        }
    return plans


def _get_plan_color(plan_name: str) -> str:
    """Get color for plan"""
    colors = {
        'free': '#6c757d',
        'basic': '#3b82f6',
        'professional': '#8b5cf6',
        'enterprise': '#10b981'
    }
    return colors.get(plan_name, '#6c757d')


def _get_plan_badge(plan_name: str) -> str:
    """Get badge emoji for plan"""
    badges = {
        'free': '🆓',
        'basic': '📊',
        'professional': '⭐',
        'enterprise': '👑'
    }
    return badges.get(plan_name, '📋')


def _get_plan_features(plan_name: str) -> List[str]:
    """Get features for plan"""
    features = {
        'free': [
            '5 analyses/month',
            'Basic Bid Optimizer',
            'Rate Viewer',
            'Basic reports',
            'Email support',
            '7-day history'
        ],
        'basic': [
            '30 analyses/month',
            'Basic Bid Optimizer',
            'Advanced Bid Optimizer',
            'AI predictions',
            'Export reports',
            '30-day history',
            'Email support'
        ],
        'professional': [
            'Unlimited analyses',
            'Competitive Bid Simulator',
            'ML predictions',
            'Competitor tracking',
            'Team collaboration',
            'Priority support',
            'API access'
        ],
        'enterprise': [
            'Everything in Professional',
            'Custom AI model',
            'Dedicated support',
            'SLA guarantee',
            'On-premise option'
        ]
    }
    return features.get(plan_name, ['Basic features'])


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_plans(force_refresh: bool = False) -> Dict[str, Dict]:
    """Get all plans (with caching)"""
    return get_plans_from_db(force_refresh)


def get_plan(plan_name: str) -> Dict:
    """Get a single plan by name"""
    plans = get_plans()
    return plans.get(plan_name, plans.get('free', {}))


def is_premium_plan(plan_name: str) -> bool:
    """Check if a plan is premium (Professional or Enterprise)"""
    return plan_name in ['professional', 'enterprise']


def get_plan_price(plan_name: str, yearly: bool = False) -> float:
    """Get plan price"""
    plan = get_plan(plan_name)
    return plan.get('price_yearly' if yearly else 'price_monthly', 0)


def get_plan_limit(plan_name: str, limit_type: str) -> int:
    """
    Get a specific limit for a plan
    
    Args:
        plan_name: Plan name
        limit_type: 'analyses', 'boq', 'bid', 'users', 'extension'
    
    Returns:
        Limit value (-1 for unlimited)
    """
    plan = get_plan(plan_name)
    
    limit_map = {
        'analyses': 'analyses_limit',
        'boq': 'max_boq_generations',
        'bid': 'max_bid_optimizations',
        'users': 'users_limit',
        'extension': 'extension_auto_fills'
    }
    
    key = limit_map.get(limit_type, 'analyses_limit')
    return plan.get(key, 5)


def refresh_plans_cache():
    """Force refresh the plans cache"""
    global _plans_cache, _plans_cache_time
    print("🔄 Refreshing plans cache...")
    _plans_cache = None
    _plans_cache_time = None
    # Force reload
    get_plans(force_refresh=True)
    print("✅ Plans cache refreshed")




