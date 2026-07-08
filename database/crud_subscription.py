# database/crud_subscription.py - Fully Fixed

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Subscription Manager using Supabase Direct"""

    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
        self.supabase = None
        
        # Try to get supabase client if available
        try:
            from database.connection import get_supabase_client, is_supabase
            if is_supabase():
                self.supabase = get_supabase_client()
        except ImportError:
            pass
    
    def _get_db(self):
        """Get the database manager"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            raise AttributeError("No database connection available")

    # ──────────────────────────────────────────────────────────────
    # PLAN MANAGEMENT
    # ──────────────────────────────────────────────────────────────

    def get_all_plans(self) -> List[Dict]:
        """Get all subscription plans from subscription_plans table"""
        try:
            if self.supabase:
                response = self.supabase.table('subscription_plans') \
                    .select('*') \
                    .order('id') \
                    .execute()
                return response.data if response.data else []
            else:
                db = self._get_db()
                return db.query("SELECT * FROM subscription_plans ORDER BY id")
        except Exception as e:
            logger.error(f"Error getting plans: {e}")
            return []

    def get_plan_by_name(self, plan_name: str) -> Optional[Dict]:
        """Get a specific plan by name"""
        try:
            if self.supabase:
                response = self.supabase.table('subscription_plans') \
                    .select('*') \
                    .eq('plan_name', plan_name) \
                    .execute()
                return response.data[0] if response.data else None
            else:
                db = self._get_db()
                result = db.query(
                    "SELECT * FROM subscription_plans WHERE plan_name = ?",
                    (plan_name,)
                )
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting plan {plan_name}: {e}")
            return None

    # ──────────────────────────────────────────────────────────────
    # COMPANY SUBSCRIPTION
    # ──────────────────────────────────────────────────────────────

    def get_company_subscription(self, company_id: int) -> Dict:
        """Get company's subscription details"""
        try:
            if self.supabase:
                # ✅ Step 1: Get subscription without JOIN
                response = self.supabase.table('subscriptions') \
                    .select('*') \
                    .eq('company_id', company_id) \
                    .order('id', desc=True) \
                    .limit(1) \
                    .execute()

                if response.data:
                    result = dict(response.data[0])
                    logger.info(f"✅ Found subscription for company {company_id}: {result.get('plan')}")
                    
                    # ✅ Step 2: Fetch plan details separately
                    plan_name = result.get('plan', 'free')
                    plan_response = self.supabase.table('subscription_plans') \
                        .select('*') \
                        .eq('plan_name', plan_name) \
                        .execute()
                    
                    if plan_response.data:
                        plan_data = plan_response.data[0]
                        # Merge plan data into result
                        for key, value in plan_data.items():
                            if key not in result or result[key] is None:
                                result[key] = value
                    
                    # ✅ Step 3: Enrich with plan details
                    return self.enrich_subscription(result)
                
                # ✅ If no subscription found, return default
                logger.warning(f"⚠️ No subscription found for company {company_id}")
                return self.get_default_subscription()
                
            else:
                # SQLite fallback
                db = self._get_db()
                result = db.query(
                    "SELECT * FROM subscriptions WHERE company_id = ? ORDER BY id DESC LIMIT 1",
                    (company_id,)
                )
                if result:
                    return self.enrich_subscription(result[0])
                return self.get_default_subscription()

        except Exception as e:
            logger.error(f"❌ Error getting company subscription for {company_id}: {e}")
            import traceback
            traceback.print_exc()
            return self.get_default_subscription()

    # ──────────────────────────────────────────────────────────────
    # USER SUBSCRIPTION
    # ──────────────────────────────────────────────────────────────

    def get_user_subscription(self, user_id: int) -> Dict:
        """Get user's subscription details"""
        try:
            if self.supabase:
                # ✅ Step 1: Get subscription without JOIN
                response = self.supabase.table('subscriptions') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .order('id', desc=True) \
                    .limit(1) \
                    .execute()

                if response.data:
                    result = dict(response.data[0])
                    
                    # ✅ Step 2: Fetch plan details separately
                    plan_name = result.get('plan', 'free')
                    plan_response = self.supabase.table('subscription_plans') \
                        .select('*') \
                        .eq('plan_name', plan_name) \
                        .execute()
                    
                    if plan_response.data:
                        plan_data = plan_response.data[0]
                        for key, value in plan_data.items():
                            if key not in result or result[key] is None:
                                result[key] = value
                    
                    return self.enrich_subscription(result)
                
                # ✅ If no user subscription, try company subscription
                user_response = self.supabase.table('users') \
                    .select('company_id') \
                    .eq('id', user_id) \
                    .execute()
                
                if user_response.data and user_response.data[0].get('company_id'):
                    company_id = user_response.data[0]['company_id']
                    return self.get_company_subscription(company_id)
                
                return self._get_default_subscription()
                
            else:
                db = self._get_db()
                result = db.query(
                    "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                )
                if result:
                    return self.enrich_subscription(result[0])
                return self._get_default_subscription()

        except Exception as e:
            logger.error(f"❌ Error getting user subscription for {user_id}: {e}")
            return self._get_default_subscription()

    # ──────────────────────────────────────────────────────────────
    # UPDATE SUBSCRIPTION
    # ──────────────────────────────────────────────────────────────

    def update_company_subscription(
        self,
        company_id: int,
        plan: str,
        duration: str = 'monthly',
        payment_method: str = 'admin',
        transaction_id: Optional[str] = None
    ) -> bool:
        """Update or create subscription for a company"""
        try:
            # ✅ Get plan details
            plan_details = self.get_plan_by_name(plan)
            if not plan_details:
                logger.error(f"Plan '{plan}' not found")
                return False

            start_date = datetime.now().date()
            if duration == 'monthly':
                end_date = start_date + timedelta(days=30)
            else:
                end_date = start_date + timedelta(days=365)
            
            trans_id = transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            if self.supabase:
                # ✅ Check if subscription exists
                response = self.supabase.table('subscriptions') \
                    .select('id') \
                    .eq('company_id', company_id) \
                    .order('id', desc=True) \
                    .limit(1) \
                    .execute()

                data = {
                    'plan': plan,
                    'status': 'active',
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'analyses_limit': plan_details.get('max_tender_analyses', 5),
                    'max_boq_generations': plan_details.get('max_boq_generations', 5),
                    'max_bid_optimizations': plan_details.get('max_bid_optimizations', 5),
                    'can_export_data': plan_details.get('can_export_data', False),
                    'can_edit_rates': plan_details.get('can_edit_rates', False),
                    'can_delete_rates': plan_details.get('can_delete_rates', False),
                    'can_create_versions': plan_details.get('can_create_versions', False),
                    'can_manage_team': plan_details.get('can_manage_team', False),
                    'payment_method': payment_method,
                    'transaction_id': trans_id,
                    'updated_at': datetime.now().isoformat()
                }

                if response.data:
                    # ✅ Update existing
                    self.supabase.table('subscriptions') \
                        .update(data) \
                        .eq('id', response.data[0]['id']) \
                        .execute()
                    logger.info(f"✅ Updated subscription for company {company_id} to {plan}")
                else:
                    # ✅ Insert new
                    data['company_id'] = company_id
                    data['user_id'] = None
                    data['analyses_used'] = 0
                    data['boq_used'] = 0
                    data['bid_optimizations_used'] = 0
                    data['last_reset_date'] = start_date.isoformat()
                    data['created_at'] = datetime.now().isoformat()

                    self.supabase.table('subscriptions') \
                        .insert(data) \
                        .execute()
                    logger.info(f"✅ Created subscription for company {company_id} with plan {plan}")

                return True
            else:
                # SQLite fallback
                db = self._get_db()
                db.execute(
                    """INSERT OR REPLACE INTO subscriptions 
                       (company_id, plan, status, start_date, end_date, 
                        analyses_limit, max_boq_generations, max_bid_optimizations,
                        can_export_data, can_edit_rates, can_delete_rates, 
                        can_create_versions, can_manage_team, payment_method, 
                        transaction_id, updated_at, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        company_id, plan, 'active', start_date, end_date,
                        plan_details.get('max_tender_analyses', 5),
                        plan_details.get('max_boq_generations', 5),
                        plan_details.get('max_bid_optimizations', 5),
                        plan_details.get('can_export_data', False),
                        plan_details.get('can_edit_rates', False),
                        plan_details.get('can_delete_rates', False),
                        plan_details.get('can_create_versions', False),
                        plan_details.get('can_manage_team', False),
                        payment_method, trans_id,
                        datetime.now(), datetime.now()
                    )
                )
                return True

        except Exception as e:
            logger.error(f"❌ Error updating company subscription: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ──────────────────────────────────────────────────────────────
    # HELPER METHODS - MUST BE PUBLIC (no underscore) for binding
    # ──────────────────────────────────────────────────────────────

    def enrich_subscription(self, subscription: Dict) -> Dict:
        """Enrich subscription with plan details"""
        default = self.get_default_subscription()
        result = {**default, **subscription}
        
        # ✅ Handle boolean fields
        boolean_fields = [
            'can_export_data', 'can_edit_rates', 'can_delete_rates',
            'can_create_versions', 'can_manage_team'
        ]
        for field in boolean_fields:
            if field in result:
                result[field] = bool(result[field])
        
        # ✅ Add alias for subscription_tier
        if 'subscription_tier' not in result and 'plan' in result:
            result['subscription_tier'] = result['plan']
        
        # ✅ Ensure max_projects is set
        if 'max_projects' not in result and 'analyses_limit' in result:
            result['max_projects'] = result['analyses_limit']
        
        return result

    def get_default_subscription(self) -> Dict:
        """Return default subscription values (free plan)"""
        # ✅ Try to get free plan from database
        plan = self.get_plan_by_name('free')
        if plan:
            return {
                'id': None,
                'plan': 'free',
                'subscription_tier': 'free',
                'status': 'active',
                'start_date': None,
                'end_date': None,
                'max_projects': plan.get('max_tender_analyses', 5),
                'analyses_used': 0,
                'analyses_limit': plan.get('max_tender_analyses', 5),
                'max_boq_generations': plan.get('max_boq_generations', 5),
                'max_bid_optimizations': plan.get('max_bid_optimizations', 5),
                'boq_used': 0,
                'bid_optimizations_used': 0,
                'can_export_data': plan.get('can_export_data', False),
                'can_edit_rates': plan.get('can_edit_rates', False),
                'can_delete_rates': plan.get('can_delete_rates', False),
                'can_create_versions': plan.get('can_create_versions', False),
                'can_manage_team': plan.get('can_manage_team', False),
                'payment_method': None,
                'transaction_id': None,
                'updated_at': None,
                'max_users': plan.get('max_users', 1),
                'extension_auto_fills': plan.get('extension_auto_fills', 5),
                'plan_name': plan.get('plan_name', 'free'),
                'monthly_price': plan.get('monthly_price', 0),
                'yearly_price': plan.get('yearly_price', 0),
                'max_tender_analyses': plan.get('max_tender_analyses', 5),
                'company_id': None,
                'user_id': None
            }
        
        # ✅ Fallback if free plan not found
        return {
            'id': None,
            'plan': 'free',
            'subscription_tier': 'free',
            'status': 'active',
            'start_date': None,
            'end_date': None,
            'max_projects': 5,
            'analyses_used': 0,
            'analyses_limit': 5,
            'max_boq_generations': 5,
            'max_bid_optimizations': 5,
            'boq_used': 0,
            'bid_optimizations_used': 0,
            'can_export_data': False,
            'can_edit_rates': False,
            'can_delete_rates': False,
            'can_create_versions': False,
            'can_manage_team': False,
            'payment_method': None,
            'transaction_id': None,
            'updated_at': None,
            'max_users': 1,
            'extension_auto_fills': 5,
            'plan_name': 'free',
            'monthly_price': 0,
            'yearly_price': 0,
            'max_tender_analyses': 5,
            'company_id': None,
            'user_id': None
        }
    def _enrich_subscription(self, subscription: Dict) -> Dict:
        """Wrapper for enrich_subscription - used by DatabaseCRUD binding"""
        return self.enrich_subscription(subscription)

    def _get_default_subscription(self) -> Dict:
        """Wrapper for get_default_subscription - used by DatabaseCRUD binding"""
        return self.get_default_subscription()
