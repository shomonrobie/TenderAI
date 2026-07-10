# database/crud_subscription.py - Refactored with Validation Methods

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Subscription Manager using Supabase Direct with Validation"""

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
                response = self.supabase.table('subscriptions') \
                    .select('*') \
                    .eq('company_id', company_id) \
                    .order('id', desc=True) \
                    .limit(1) \
                    .execute()

                if response.data:
                    result = dict(response.data[0])
                    logger.info(f"✅ Found subscription for company {company_id}: {result.get('plan')}")
                    
                    # Fetch plan details separately
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
                
                logger.warning(f"⚠️ No subscription found for company {company_id}")
                return self.get_default_subscription()
                
            else:
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
            return self.get_default_subscription()

    # ──────────────────────────────────────────────────────────────
    # USER SUBSCRIPTION
    # ──────────────────────────────────────────────────────────────

    def get_user_subscription(self, user_id: int) -> Dict:
        """Get user's subscription details"""
        try:
            if self.supabase:
                response = self.supabase.table('subscriptions') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .order('id', desc=True) \
                    .limit(1) \
                    .execute()

                if response.data:
                    result = dict(response.data[0])
                    
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
                
                # If no user subscription, try company subscription
                user_response = self.supabase.table('users') \
                    .select('company_id') \
                    .eq('id', user_id) \
                    .execute()
                
                if user_response.data and user_response.data[0].get('company_id'):
                    company_id = user_response.data[0]['company_id']
                    return self.get_company_subscription(company_id)
                
                return self.get_default_subscription()
                
            else:
                db = self._get_db()
                result = db.query(
                    "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                )
                if result:
                    return self.enrich_subscription(result[0])
                return self.get_default_subscription()

        except Exception as e:
            logger.error(f"❌ Error getting user subscription for {user_id}: {e}")
            return self.get_default_subscription()

    # ──────────────────────────────────────────────────────────────
    # VALIDATION METHODS (NEW)
    # ──────────────────────────────────────────────────────────────

    def validate_user_subscription(self, user_id: int) -> Tuple[bool, str]:
        """
        Validate that a user has proper subscription based on their account type.
        
        Args:
            user_id: User ID to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get user from database
            if self.supabase:
                user_response = self.supabase.table('users') \
                    .select('company_id, account_type') \
                    .eq('id', user_id) \
                    .execute()
                
                if not user_response.data:
                    return False, "User not found"
                
                user = user_response.data[0]
            else:
                db = self._get_db()
                result = db.query(
                    "SELECT company_id, account_type FROM users WHERE id = ?",
                    (user_id,)
                )
                if not result:
                    return False, "User not found"
                user = result[0]
            
            # If user belongs to a company, they use company subscription
            if user.get('company_id'):
                company_sub = self.get_company_subscription(user.get('company_id'))
                if not company_sub or company_sub.get('status') != 'active':
                    return False, "Company has no active subscription"
                
                # Check if subscription is expired
                if company_sub.get('end_date'):
                    from datetime import date
                    if isinstance(company_sub.get('end_date'), str):
                        end_date = date.fromisoformat(company_sub.get('end_date'))
                    else:
                        end_date = company_sub.get('end_date')
                    if end_date < date.today():
                        return False, "Company subscription has expired"
                
                return True, "Company subscription active"
            
            # Individual users must have their own subscription
            if user.get('account_type') == 'individual':
                user_sub = self.get_user_subscription(user_id)
                if not user_sub or user_sub.get('status') != 'active':
                    return False, "Individual user requires an active subscription"
                
                # Check if subscription is expired
                if user_sub.get('end_date'):
                    from datetime import date
                    if isinstance(user_sub.get('end_date'), str):
                        end_date = date.fromisoformat(user_sub.get('end_date'))
                    else:
                        end_date = user_sub.get('end_date')
                    if end_date < date.today():
                        return False, "User subscription has expired"
                
                return True, "Individual subscription active"
            
            # Company users with no company_id
            if user.get('account_type') == 'company' and not user.get('company_id'):
                return False, "Company user has no company assigned"
            
            return False, f"Unknown account type: {user.get('account_type')}"
            
        except Exception as e:
            logger.error(f"Error validating user subscription: {e}")
            return False, f"Validation error: {str(e)}"

    def check_user_subscription_status(self, user_id: int) -> Dict:
        """
        Get comprehensive subscription status for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with subscription status details
        """
        try:
            # Get user
            if self.supabase:
                user_response = self.supabase.table('users') \
                    .select('company_id, account_type') \
                    .eq('id', user_id) \
                    .execute()
                
                if not user_response.data:
                    return {'has_subscription': False, 'message': 'User not found'}
                
                user = user_response.data[0]
            else:
                db = self._get_db()
                result = db.query(
                    "SELECT company_id, account_type FROM users WHERE id = ?",
                    (user_id,)
                )
                if not result:
                    return {'has_subscription': False, 'message': 'User not found'}
                user = result[0]
            
            # If user has company, check company subscription
            if user.get('company_id'):
                sub = self.get_company_subscription(user.get('company_id'))
                if sub and sub.get('status') == 'active':
                    return {
                        'has_subscription': True,
                        'type': 'company',
                        'subscription': sub,
                        'status': sub.get('status'),
                        'plan': sub.get('plan'),
                        'plan_name': sub.get('plan_name'),
                        'end_date': sub.get('end_date'),
                        'analyses_limit': sub.get('analyses_limit'),
                        'analyses_used': sub.get('analyses_used', 0)
                    }
                else:
                    return {
                        'has_subscription': False,
                        'type': 'company',
                        'message': 'No active subscription found for company'
                    }
            
            # Individual user - check personal subscription
            sub = self.get_user_subscription(user_id)
            if sub and sub.get('status') == 'active':
                return {
                    'has_subscription': True,
                    'type': 'individual',
                    'subscription': sub,
                    'status': sub.get('status'),
                    'plan': sub.get('plan'),
                    'plan_name': sub.get('plan_name'),
                    'end_date': sub.get('end_date'),
                    'analyses_limit': sub.get('analyses_limit'),
                    'analyses_used': sub.get('analyses_used', 0)
                }
            else:
                return {
                    'has_subscription': False,
                    'type': 'individual',
                    'message': 'No active subscription found for user'
                }
                
        except Exception as e:
            logger.error(f"Error checking subscription status: {e}")
            return {'has_subscription': False, 'message': f'Error: {str(e)}'}

    def can_user_access_feature(self, user_id: int, feature: str) -> bool:
        """
        Check if a user can access a specific feature based on their subscription.
        
        Args:
            user_id: User ID
            feature: Feature name (e.g., 'edit_rates', 'export_data')
        
        Returns:
            True if user can access, False otherwise
        """
        status = self.check_user_subscription_status(user_id)
        
        if not status.get('has_subscription'):
            return False
        
        sub = status.get('subscription')
        if not sub:
            return False
        
        # Map features to subscription columns
        feature_map = {
            'edit_rates': 'can_edit_rates',
            'delete_rates': 'can_delete_rates',
            'create_versions': 'can_create_versions',
            'export_data': 'can_export_data',
            'manage_team': 'can_manage_team'
        }
        
        column = feature_map.get(feature)
        if not column:
            return False
        
        return sub.get(column, False)

    def get_user_subscription_usage(self, user_id: int) -> Dict:
        """
        Get subscription usage statistics for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with usage statistics
        """
        status = self.check_user_subscription_status(user_id)
        
        if not status.get('has_subscription'):
            return {
                'has_subscription': False,
                'message': 'No active subscription'
            }
        
        sub = status.get('subscription')
        if not sub:
            return {
                'has_subscription': False,
                'message': 'No subscription data'
            }
        
        return {
            'has_subscription': True,
            'analyses_used': sub.get('analyses_used', 0),
            'analyses_limit': sub.get('analyses_limit', 0),
            'analyses_remaining': max(0, sub.get('analyses_limit', 0) - sub.get('analyses_used', 0)),
            'boq_used': sub.get('boq_used', 0),
            'max_boq_generations': sub.get('max_boq_generations', 0),
            'boq_remaining': max(0, sub.get('max_boq_generations', 0) - sub.get('boq_used', 0)),
            'bid_optimizations_used': sub.get('bid_optimizations_used', 0),
            'max_bid_optimizations': sub.get('max_bid_optimizations', 0),
            'bid_optimizations_remaining': max(0, sub.get('max_bid_optimizations', 0) - sub.get('bid_optimizations_used', 0)),
            'plan_name': status.get('plan_name'),
            'plan': status.get('plan'),
            'end_date': status.get('end_date')
        }

    def increment_user_analyses_used(self, user_id: int) -> bool:
        """
        Increment the analyses_used count for a user's subscription.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get subscription for user
            if self.supabase:
                # Check if user has company subscription first
                user_response = self.supabase.table('users') \
                    .select('company_id') \
                    .eq('id', user_id) \
                    .execute()
                
                if user_response.data and user_response.data[0].get('company_id'):
                    company_id = user_response.data[0]['company_id']
                    # Update company subscription
                    response = self.supabase.table('subscriptions') \
                        .select('id, analyses_limit, analyses_used') \
                        .eq('company_id', company_id) \
                        .eq('status', 'active') \
                        .order('id', desc=True) \
                        .limit(1) \
                        .execute()
                else:
                    # Update user subscription
                    response = self.supabase.table('subscriptions') \
                        .select('id, analyses_limit, analyses_used') \
                        .eq('user_id', user_id) \
                        .eq('status', 'active') \
                        .order('id', desc=True) \
                        .limit(1) \
                        .execute()
                
                if not response.data:
                    return False
                
                sub = response.data[0]
                
                # Check if limit exceeded
                if sub.get('analyses_used', 0) >= sub.get('analyses_limit', 0):
                    return False
                
                # Increment usage
                self.supabase.table('subscriptions') \
                    .update({
                        'analyses_used': sub.get('analyses_used', 0) + 1,
                        'updated_at': datetime.now().isoformat()
                    }) \
                    .eq('id', sub.get('id')) \
                    .execute()
                
                return True
            else:
                # SQLite fallback
                db = self._get_db()
                
                # Get subscription
                result = db.query(
                    """SELECT id, analyses_limit, analyses_used FROM subscriptions 
                       WHERE user_id = ? AND status = 'active' 
                       ORDER BY id DESC LIMIT 1""",
                    (user_id,)
                )
                
                if not result:
                    return False
                
                sub = result[0]
                
                if sub.get('analyses_used', 0) >= sub.get('analyses_limit', 0):
                    return False
                
                db.execute(
                    "UPDATE subscriptions SET analyses_used = analyses_used + 1, updated_at = ? WHERE id = ?",
                    (datetime.now(), sub.get('id'))
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error incrementing analyses used: {e}")
            return False

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
                    self.supabase.table('subscriptions') \
                        .update(data) \
                        .eq('id', response.data[0]['id']) \
                        .execute()
                    logger.info(f"✅ Updated subscription for company {company_id} to {plan}")
                else:
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
            return False

    # ──────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ──────────────────────────────────────────────────────────────

    def enrich_subscription(self, subscription: Dict) -> Dict:
        """Enrich subscription with plan details"""
        default = self.get_default_subscription()
        result = {**default, **subscription}
        
        boolean_fields = [
            'can_export_data', 'can_edit_rates', 'can_delete_rates',
            'can_create_versions', 'can_manage_team'
        ]
        for field in boolean_fields:
            if field in result:
                result[field] = bool(result[field])
        
        if 'subscription_tier' not in result and 'plan' in result:
            result['subscription_tier'] = result['plan']
        
        if 'max_projects' not in result and 'analyses_limit' in result:
            result['max_projects'] = result['analyses_limit']
        
        return result

    def get_default_subscription(self) -> Dict:
        """Return default subscription values (free plan)"""
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

    def get_all_subscriptions(self) -> List[Dict]:
        """Get all subscriptions for admin - returns dictionaries"""
        try:
            if self.supabase:
                response = self.supabase.table('subscriptions') \
                    .select('*, users(id, username, email, full_name), companies(id, company_name)') \
                    .order('updated_at', desc=True) \
                    .execute()
                
                if not response.data:
                    return []
                
                results = []
                for sub in response.data:
                    user = sub.get('users', {}) or {}
                    company = sub.get('companies', {}) or {}
                    
                    results.append({
                        'id': sub.get('id'),
                        'user_id': sub.get('user_id'),
                        'plan': sub.get('plan'),
                        'status': sub.get('status'),
                        'start_date': sub.get('start_date'),
                        'end_date': sub.get('end_date'),
                        'analyses_used': sub.get('analyses_used'),
                        'analyses_limit': sub.get('analyses_limit'),
                        'company_id': sub.get('company_id'),
                        'created_at': sub.get('created_at'),
                        'username': user.get('username', 'N/A'),
                        'email': user.get('email', 'N/A'),
                        'full_name': user.get('full_name', 'N/A'),
                        'company_name': company.get('company_name', 'N/A')
                    })
                
                return results
            
            else:
                db = self._get_db()
                results = db.query('''
                    SELECT 
                        s.id, s.user_id, s.plan, s.status, s.start_date, s.end_date, 
                        s.analyses_used, s.analyses_limit, s.company_id, s.created_at,
                        COALESCE(u.username, 'N/A') as username,
                        COALESCE(u.email, 'N/A') as email,
                        COALESCE(u.full_name, 'N/A') as full_name,
                        COALESCE(c.company_name, 'N/A') as company_name
                    FROM subscriptions s
                    LEFT JOIN users u ON s.user_id = u.id
                    LEFT JOIN companies c ON s.company_id = c.id
                    ORDER BY s.updated_at DESC
                ''')
                
                return [
                    {
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'plan': row['plan'],
                        'status': row['status'],
                        'start_date': row['start_date'],
                        'end_date': row['end_date'],
                        'analyses_used': row['analyses_used'],
                        'analyses_limit': row['analyses_limit'],
                        'company_id': row['company_id'],
                        'created_at': row['created_at'],
                        'username': row['username'],
                        'email': row['email'],
                        'full_name': row['full_name'],
                        'company_name': row['company_name']
                    }
                    for row in results
                ]
                    
        except Exception as e:
            logger.error(f"Error getting all subscriptions: {e}")
            return []
    def update_user_subscription(
        self,
        user_id: int,
        plan: str,
        duration: str = 'monthly',
        payment_method: str = 'admin',
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Update or create subscription for an individual user.
        
        Args:
            user_id: User ID
            plan: Plan name (must exist in subscription_plans)
            duration: 'monthly' or 'yearly'
            payment_method: Payment method
            transaction_id: Optional transaction ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get plan details
            plan_details = self.get_plan_by_name(plan)
            if not plan_details:
                logger.error(f"Plan '{plan}' not found")
                return False

            start_date = datetime.now().date()
            if duration == 'monthly':
                end_date = start_date + timedelta(days=30)
            else:
                end_date = start_date + timedelta(days=365)
            
            trans_id = transaction_id or f"ADMIN_USER_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            if self.supabase:
                # Check if subscription already exists for this user
                response = self.supabase.table('subscriptions') \
                    .select('id') \
                    .eq('user_id', user_id) \
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
                    # Update existing subscription
                    self.supabase.table('subscriptions') \
                        .update(data) \
                        .eq('id', response.data[0]['id']) \
                        .execute()
                    logger.info(f"✅ Updated subscription for user {user_id} to {plan}")
                else:
                    # Insert new subscription
                    data['user_id'] = user_id
                    data['company_id'] = None
                    data['analyses_used'] = 0
                    data['boq_used'] = 0
                    data['bid_optimizations_used'] = 0
                    data['last_reset_date'] = start_date.isoformat()
                    data['created_at'] = datetime.now().isoformat()

                    self.supabase.table('subscriptions') \
                        .insert(data) \
                        .execute()
                    logger.info(f"✅ Created subscription for user {user_id} with plan {plan}")

                return True
            else:
                # SQLite fallback
                db = self._get_db()
                
                # Check if exists
                existing = db.query(
                    "SELECT id FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                )
                
                if existing:
                    # Update existing
                    db.execute(
                        """UPDATE subscriptions SET 
                            plan = ?, status = 'active', start_date = ?, end_date = ?,
                            analyses_limit = ?, max_boq_generations = ?, max_bid_optimizations = ?,
                            can_export_data = ?, can_edit_rates = ?, can_delete_rates = ?,
                            can_create_versions = ?, can_manage_team = ?,
                            payment_method = ?, transaction_id = ?, updated_at = ?
                        WHERE user_id = ?""",
                        (
                            plan, start_date, end_date,
                            plan_details.get('max_tender_analyses', 5),
                            plan_details.get('max_boq_generations', 5),
                            plan_details.get('max_bid_optimizations', 5),
                            plan_details.get('can_export_data', False),
                            plan_details.get('can_edit_rates', False),
                            plan_details.get('can_delete_rates', False),
                            plan_details.get('can_create_versions', False),
                            plan_details.get('can_manage_team', False),
                            payment_method, trans_id,
                            datetime.now(), user_id
                        )
                    )
                else:
                    # Insert new
                    db.execute(
                        """INSERT INTO subscriptions 
                        (user_id, plan, status, start_date, end_date, 
                            analyses_limit, max_boq_generations, max_bid_optimizations,
                            can_export_data, can_edit_rates, can_delete_rates, 
                            can_create_versions, can_manage_team, payment_method, 
                            transaction_id, analyses_used, boq_used, bid_optimizations_used,
                            last_reset_date, created_at, updated_at)
                        VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?)""",
                        (
                            user_id, plan, start_date, end_date,
                            plan_details.get('max_tender_analyses', 5),
                            plan_details.get('max_boq_generations', 5),
                            plan_details.get('max_bid_optimizations', 5),
                            plan_details.get('can_export_data', False),
                            plan_details.get('can_edit_rates', False),
                            plan_details.get('can_delete_rates', False),
                            plan_details.get('can_create_versions', False),
                            plan_details.get('can_manage_team', False),
                            payment_method, trans_id,
                            start_date, datetime.now(), datetime.now()
                        )
                    )
                
                return True

        except Exception as e:
            logger.error(f"❌ Error updating user subscription: {e}")
            import traceback
            traceback.print_exc()
            return False
