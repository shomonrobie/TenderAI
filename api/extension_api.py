# api/extension_api.py - Complete updated version with all auto-fill endpoints

from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta
import logging
import os

from database.unified_db_manager import get_db_manager
from database.crud_autofill import AutoFillCRUD

extension_bp = Blueprint('extension', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_EXPIRATION_HOURS = 24


def get_db():
    """Get database manager instance"""
    return get_db_manager()


def get_autofill():
    """Get AutoFillCRUD instance"""
    return AutoFillCRUD(get_db())


def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header[7:]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.company_id = payload['company_id']
            request.user_role = payload['role']
            request.username = payload.get('username', '')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# HEALTH CHECK
# =============================================================================

@extension_bp.route('/health', methods=['GET', 'HEAD'])
def health_check():
    """Health check endpoint for extension auto-detection"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


# =============================================================================
# AUTHENTICATION
# =============================================================================

@extension_bp.route('/auth/login', methods=['POST'])
def extension_login():
    """Authenticate extension user and return JWT"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    db = get_db()
    
    # Authenticate using existing auth system
    user, status, message = db.authenticate_user(username, password)
    
    if not user:
        return jsonify({'success': False, 'message': message or 'Invalid credentials'}), 401
    
    # Check if user is approved
    is_approved = user[9] if len(user) > 9 else 1
    if not is_approved:
        return jsonify({'success': False, 'message': 'Account pending approval'}), 403
    
    # Get subscription info
    subscription = db.get_user_subscription(user.get('id'))
    plan = subscription.get('plan', 'free')
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user[0],
        'company_id': user[6],
        'role': user[4],
        'username': user[1],
        'email': user[2],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'full_name': user[3],
            'role': user[4],
            'company_id': user[6],
            'plan': plan
        }
    })


@extension_bp.route('/auth/auto-login', methods=['POST'])
@require_auth
def auto_login():
    """Auto-login for already authenticated users (no password required)"""
    try:
        db = get_db()
        subscription = db.get_user_subscription(request.user_id)
        plan = subscription.get('plan', 'free')
        
        return jsonify({
            'success': True,
            'token': request.headers.get('Authorization', '').replace('Bearer ', ''),
            'user': {
                'id': request.user_id,
                'company_id': request.company_id,
                'role': request.user_role,
                'username': request.username,
                'plan': plan
            }
        })
    except Exception as e:
        logger.error(f"Auto-login error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# =============================================================================
# AUTO-FILL DATA ENDPOINTS
# =============================================================================

@extension_bp.route('/auto-fill/<data_type>', methods=['GET'])
@require_auth
def get_auto_fill_data(data_type):
    """Get data for auto-filling forms"""
    search_term = request.args.get('search')
    limit = request.args.get('limit', 50, type=int)
    company_id = request.company_id
    user_id = request.user_id
    
    autofill = get_autofill()
    
    # Map data_type to AutoFillCRUD method
    data_map = {
        'company': lambda: autofill.get_company_data(company_id),
        'company_extended': lambda: autofill.get_company_extended_data(company_id),
        'personnel': lambda: autofill.get_personnel_data(company_id, search_term, limit),
        'personnel_detailed': lambda: autofill.get_personnel_detailed_data(company_id, search_term, limit),
        'key_personnel': lambda: autofill.get_key_personnel_data(company_id),
        'equipment': lambda: autofill.get_equipment_data(company_id, search_term, limit),
        'experience': lambda: autofill.get_experience_data(company_id, search_term, limit),
        'experience_comparison': lambda: autofill.get_experience_for_comparison(company_id),
        'financial': lambda: autofill.get_financial_data(company_id),
        'financial_detailed': lambda: autofill.get_financial_detailed_data(company_id),
        'liquid_assets': lambda: autofill.get_liquid_assets(company_id),
        'licenses': lambda: autofill.get_license_data(company_id),
        'ongoing_works': lambda: autofill.get_ongoing_works_data(company_id),
        'references': lambda: autofill.get_references_data(company_id),
        'all': lambda: autofill.get_all_company_data(company_id),
    }
    
    if data_type not in data_map:
        return jsonify({'error': f'Unknown data type: {data_type}'}), 400
    
    try:
        data = data_map[data_type]()
        
        # Track usage
        autofill.track_form_fill(company_id, user_id, {
            'form_type': data_type,
            'field_label': f'auto_fill_{data_type}',
            'confidence': 1.0,
            'url': request.referrer or ''
        })
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in auto-fill {data_type}: {e}")
        return jsonify({'error': str(e)}), 500


@extension_bp.route('/auto-fill/all-data', methods=['GET'])
@require_auth
def get_all_auto_fill_data():
    """Get all company data for auto-fill in one request using the view"""
    try:
        db = get_db()
        
        result = db.query_one("""
            SELECT * FROM vw_company_auto_fill_data 
            WHERE company_id = ?
        """, (request.company_id,))
        
        if result:
            # Track usage
            autofill = get_autofill()
            autofill.track_form_fill(
                request.company_id,
                request.user_id,
                {
                    'form_type': 'all_data',
                    'field_label': 'auto_fill_all_data',
                    'confidence': 1.0,
                    'url': request.referrer or ''
                }
            )
            
            return jsonify({
                'success': True,
                'data': dict(result)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No data found for company'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting all auto-fill data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# AUTO-FILL SETTINGS
# =============================================================================

@extension_bp.route('/auto-fill/settings', methods=['GET', 'POST', 'PUT'])
@require_auth
def manage_auto_fill_settings():
    """Get or update auto-fill settings"""
    autofill = get_autofill()
    
    if request.method == 'GET':
        # Get settings
        settings = autofill.get_auto_fill_settings(request.company_id)
        return jsonify(settings)
    
    elif request.method in ['POST', 'PUT']:
        # Update settings
        data = request.get_json()
        
        # Validate data
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update settings
        success = autofill.update_auto_fill_settings(
            request.company_id,
            {
                'auto_fill_email': data.get('auto_fill_email'),
                'default_bid_amount': data.get('default_bid_amount'),
                'default_contract_role': data.get('default_contract_role', 'Sole')
            }
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Auto-fill settings updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update settings'}), 500


# =============================================================================
# FIELD MATCHING
# =============================================================================

@extension_bp.route('/match-field', methods=['POST'])
@require_auth
def match_field():
    """Match a form field label to company data"""
    data = request.get_json()
    label = data.get('label', '')
    field_type = data.get('fieldType', 'text')
    
    autofill = get_autofill()
    match = autofill.match_field_to_data(label, field_type)
    
    if match and match.get('source') and match.get('confidence', 0) > 0.5:
        value = autofill.get_field_value(request.company_id, match['source'], match['field'])
        match['display_value'] = value
    
    return jsonify({'match': match})


@extension_bp.route('/get-fill-value', methods=['POST'])
@require_auth
def get_fill_value():
    """Get actual value to fill for a matched field"""
    data = request.get_json()
    source = data.get('source')
    field = data.get('field')
    
    autofill = get_autofill()
    value = autofill.get_field_value(request.company_id, source, field)
    
    return jsonify({'value': value})


# =============================================================================
# KNOWLEDGE SEARCH
# =============================================================================

@extension_bp.route('/knowledge/search', methods=['GET'])
@require_auth
def search_knowledge_base():
    """Search company knowledge base"""
    query = request.args.get('q', '')
    categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
    
    if not query:
        return jsonify({'results': []})
    
    autofill = get_autofill()
    results = autofill.search_company_data(request.company_id, query, categories)
    
    return jsonify({'results': results})


# =============================================================================
# TRACKING ENDPOINTS
# =============================================================================

@extension_bp.route('/track/form-fill', methods=['POST'])
@require_auth
def track_form_fill():
    """Track form fill events for analytics and usage counting"""
    data = request.get_json()
    
    autofill = get_autofill()
    success = autofill.track_form_fill(
        request.company_id,
        request.user_id,
        {
            'field_label': data.get('field_label', ''),
            'field_value': data.get('field_value', ''),
            'confidence': data.get('confidence', 0),
            'url': data.get('url', ''),
            'form_type': data.get('form_type', '')
        }
    )
    
    return jsonify({'success': success})


@extension_bp.route('/usage/stats', methods=['GET'])
@require_auth
def get_extension_usage():
    """Get extension usage statistics for current company"""
    try:
        db = get_db()
        autofill = get_autofill()
        
        usage = autofill.get_usage_stats(request.company_id, request.user_id)
        
        # Get subscription plan
        subscription = db.get_user_subscription(request.user_id)
        plan = subscription.get('plan', 'free')
        
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1
        }
        limit = plan_limits.get(plan, 5)
        
        return jsonify({
            'usage': {
                'used': usage.get('used', 0),
                'limit': limit,
                'remaining': -1 if limit == -1 else max(0, limit - usage.get('used', 0)),
                'is_unlimited': limit == -1
            },
            'plan': plan,
            'plan_name': plan.capitalize()
        })
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        return jsonify({'usage': {'used': 0, 'limit': 5, 'remaining': 5, 'is_unlimited': False}})


@extension_bp.route('/track/submission', methods=['POST'])
@require_auth
def track_tender_submission():
    """Track tender submission for analytics"""
    data = request.get_json()
    
    autofill = get_autofill()
    success = autofill.track_tender_submission(
        request.company_id,
        {
            'tender_id': data.get('tender_id'),
            'tender_title': data.get('tender_title'),
            'procuring_entity': data.get('procuring_entity'),
            'submission_date': data.get('submission_date'),
            'bid_amount': data.get('bid_amount'),
            'status': data.get('status', 'submitted'),
            'auto_fill_used': data.get('auto_fill_used', False),
            'auto_fill_count': data.get('auto_fill_count', 0)
        }
    )
    
    return jsonify({'success': success})


@extension_bp.route('/company/stats', methods=['GET'])
@require_auth
def get_company_stats():
    """Get company statistics for extension display"""
    try:
        db = get_db()
        autofill = get_autofill()
        
        # Get user count
        result = db.query_one(
            "SELECT COUNT(*) as total FROM users WHERE company_id = ? AND is_active = 1",
            (request.company_id,)
        )
        user_count = result.get('total', 0) if result else 0
        
        # Get tender count
        result = db.query_one(
            "SELECT COUNT(*) as total FROM company_tenders WHERE company_id = ?",
            (request.company_id,)
        )
        tender_count = result.get('total', 0) if result else 0
        
        # Get analysis count
        result = db.query_one(
            "SELECT COUNT(*) as total FROM tender_analyses WHERE company_id = ?",
            (request.company_id,)
        )
        analysis_count = result.get('total', 0) if result else 0
        
        # Get auto-fill usage
        usage = autofill.get_usage_stats(request.company_id)
        
        return jsonify({
            'total_users': user_count,
            'total_tenders': tender_count,
            'total_analyses': analysis_count,
            'auto_fill_this_month': usage.get('used', 0)
        })
        
    except Exception as e:
        logger.error(f"Error getting company stats: {e}")
        return jsonify({})


# =============================================================================
# FILE UPLOAD
# =============================================================================

@extension_bp.route('/upload/contract', methods=['POST'])
@require_auth
def upload_contract_agreement():
    """Upload contract agreement file for ongoing works"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        work_id = request.form.get('work_id')
        contract_number = request.form.get('contract_number')
        
        # Save file
        upload_dir = f"data/uploads/contracts/{request.company_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = file.filename.replace(" ", "_")
        file_path = f"{upload_dir}/{timestamp}_{safe_name}"
        
        file.save(file_path)
        
        autofill = get_autofill()
        success = False
        
        if work_id:
            success = autofill.update_contract_agreement(
                request.company_id, int(work_id), file_path, file.filename
            )
        elif contract_number:
            success = autofill.update_experience_contract(
                request.company_id, contract_number, file_path
            )
        else:
            return jsonify({'error': 'work_id or contract_number required'}), 400
        
        if success:
            return jsonify({
                'success': True,
                'file_path': file_path,
                'file_name': file.filename
            })
        else:
            return jsonify({'error': 'Failed to update record'}), 500
        
    except Exception as e:
        logger.error(f"Error uploading contract: {e}")
        return jsonify({'error': str(e)}), 500