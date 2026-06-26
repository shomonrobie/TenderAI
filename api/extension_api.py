# api/extension_api.py - Complete updated version

from flask import Blueprint, request, jsonify, send_file
from functools import wraps
import jwt
from datetime import datetime, timedelta
import logging
import io
import os

from database.unified_db_manager import UnifiedDatabaseManager

from modules.field_matcher import field_matcher

extension_bp = Blueprint('extension', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_EXPIRATION_HOURS = 24

db = UnifiedDatabaseManager()


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
# HEALTH CHECK ENDPOINT (For extension auto-detection)
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
# AUTHENTICATION ENDPOINTS
# =============================================================================

@extension_bp.route('/auth/login', methods=['POST'])
def extension_login():
    """Authenticate extension user and return JWT"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    # Authenticate using existing auth system
    user, status, message = db.authenticate_user(username, password)
    
    if not user:
        return jsonify({'success': False, 'message': message or 'Invalid credentials'}), 401
    
    # Check if user is approved
    is_approved = user[9] if len(user) > 9 else 1
    if not is_approved:
        return jsonify({'success': False, 'message': 'Account pending approval'}), 403
    
    # Get subscription info
    #subscription = db.get_user_subscription(user[0])
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


@extension_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify JWT token validity"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'valid': False}), 401
    
    token = auth_header[7:]
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return jsonify({'valid': True, 'user_id': payload['user_id']})
    except:
        return jsonify({'valid': False}), 401


# =============================================================================
# AUTO-FILL DATA ENDPOINTS
# =============================================================================

@extension_bp.route('/auto-fill/<data_type>', methods=['GET'])
@require_auth
def get_auto_fill_data(data_type):
    """Get data for auto-filling forms with usage check"""
    search_term = request.args.get('search')
    
    # Get company data
    data = {}
    
    if data_type == 'personnel':
        # Get personnel data
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, designation, employee_id, skills
            FROM personnel
            WHERE company_id = ? AND employment_status = 'active'
            ORDER BY full_name
            LIMIT 50
        """, (request.company_id,))
        
        personnel = []
        for row in cursor.fetchall():
            personnel.append({
                'id': row[0],
                'name': row[1],
                'designation': row[2],
                'employee_id': row[3],
                'skills': row[4] if row[4] else ''
            })
        data['personnel'] = personnel
        conn.close()
    
    elif data_type == 'equipment':
        # Get equipment data
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, equipment_name, equipment_type, model, capacity, current_status
            FROM equipment
            WHERE company_id = ? AND current_status = 'available'
            ORDER BY equipment_name
            LIMIT 50
        """, (request.company_id,))
        
        equipment = []
        for row in cursor.fetchall():
            equipment.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'model': row[3],
                'capacity': row[4],
                'status': row[5]
            })
        data['equipment'] = equipment
        conn.close()
    
    elif data_type == 'experience':
        # Get experience data
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, project_name, client_name, contract_value, completion_date
            FROM experience_record
            WHERE company_id = ? AND is_completed = 1
            ORDER BY completion_date DESC
            LIMIT 20
        """, (request.company_id,))
        
        experiences = []
        for row in cursor.fetchall():
            experiences.append({
                'id': row[0],
                'project': row[1],
                'client': row[2],
                'value': row[3],
                'date': row[4]
            })
        data['experiences'] = experiences
        conn.close()
    
    elif data_type == 'financial':
        # Get financial data
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fiscal_year, annual_turnover, net_worth, working_capital, credit_limit
            FROM financial_capacity
            WHERE company_id = ?
            ORDER BY fiscal_year DESC
            LIMIT 3
        """, (request.company_id,))
        
        financial = []
        for row in cursor.fetchall():
            financial.append({
                'year': row[0],
                'turnover': row[1],
                'net_worth': row[2],
                'working_capital': row[3],
                'credit_limit': row[4]
            })
        data['financial'] = financial
        conn.close()
    
    elif data_type == 'company':
        # Get company profile
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT company_name, registration_number, vat_number, email, phone, address, division
            FROM companies
            WHERE id = ?
        """, (request.company_id,))
        
        row = cursor.fetchone()
        if row:
            data['company'] = {
                'name': row[0],
                'registration_number': row[1],
                'vat_number': row[2],
                'email': row[3],
                'phone': row[4],
                'address': row[5],
                'division': row[6]
            }
        conn.close()
    
    return jsonify(data)


@extension_bp.route('/match-field', methods=['POST'])
@require_auth
def match_field():
    """Match a form field label to company data"""
    data = request.get_json()
    label = data.get('label', '')
    field_type = data.get('fieldType', 'text')
    
    match = field_matcher.match_field(label, field_type)
    
    if match and match.get('source'):
        # Get actual value if match is good
        if match.get('confidence', 0) > 0.5:
            value = get_field_value(request.company_id, match['source'], match['field'])
            match['display_value'] = value
    
    return jsonify({'match': match})


@extension_bp.route('/get-fill-value', methods=['POST'])
@require_auth
def get_fill_value():
    """Get actual value to fill for a matched field"""
    data = request.get_json()
    source = data.get('source')
    field = data.get('field')
    
    value = get_field_value(request.company_id, source, field)
    
    return jsonify({'value': value})


@extension_bp.route('/knowledge/search', methods=['GET'])
@require_auth
def search_knowledge_base():
    """Search company knowledge base"""
    query = request.args.get('q', '')
    categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
    
    if not query:
        return jsonify({'results': []})
    
    results = search_company_data(request.company_id, query, categories)
    
    return jsonify({'results': results})

@extension_bp.route('/track/form-fill', methods=['POST'])
@require_auth
def track_form_fill():
    """Track form fill events for analytics and usage counting"""
    data = request.get_json()
    
    # Log the fill to extension_auto_fill_log
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO extension_auto_fill_log 
            (company_id, user_id, field_label, confidence_score, page_url, filled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.company_id,
            request.user_id,
            data.get('field_label', ''),
            data.get('confidence', 0),
            data.get('url', ''),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error tracking form fill: {e}")
    
    return jsonify({'success': True})


@extension_bp.route('/usage/stats', methods=['GET'])
@require_auth
def get_extension_usage():
    """Get extension usage statistics for current company"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current month usage
        this_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT COUNT(*) FROM extension_auto_fill_log 
            WHERE company_id = ? AND filled_at >= ?
        """, (request.company_id, this_month))
        
        used = cursor.fetchone()[0] or 0
        conn.close()
        
        # Get subscription plan
        sub = db.get_company_subscription(request.company_id)
        plan = sub.get('plan', 'free')
        
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1
        }
        limit = plan_limits.get(plan, 5)
        
        return jsonify({
            'usage': {
                'used': used,
                'limit': limit,
                'remaining': -1 if limit == -1 else max(0, limit - used),
                'is_unlimited': limit == -1
            },
            'plan': plan,
            'plan_name': plan.capitalize()
        })
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        return jsonify({'usage': {'used': 0, 'limit': 5, 'remaining': 5, 'is_unlimited': False}})


@extension_bp.route('/company/stats', methods=['GET'])
@require_auth
def get_company_stats():
    """Get company statistics for extension display"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM users WHERE company_id = ? AND is_active = 1", (request.company_id,))
        user_count = cursor.fetchone()[0] or 0
        
        # Get tender count
        cursor.execute("SELECT COUNT(*) FROM company_tenders WHERE company_id = ?", (request.company_id,))
        tender_count = cursor.fetchone()[0] or 0
        
        # Get analysis count
        cursor.execute("SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?", (request.company_id,))
        analysis_count = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'total_users': user_count,
            'total_tenders': tender_count,
            'total_analyses': analysis_count
        })
        
    except Exception as e:
        logger.error(f"Error getting company stats: {e}")
        return jsonify({})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_field_value(company_id, source, field):
    """Get actual value from database for a matched field"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        value = None
        
        if source == 'personnel':
            # Get first key personnel
            cursor.execute("""
                SELECT full_name FROM personnel 
                WHERE company_id = ? AND employment_status = 'active' 
                ORDER BY is_key_personnel DESC, full_name
                LIMIT 1
            """, (company_id,))
            row = cursor.fetchone()
            if row:
                value = row[0]
        
        elif source == 'equipment':
            # Get equipment list as comma-separated
            cursor.execute("""
                SELECT equipment_name FROM equipment 
                WHERE company_id = ? AND current_status = 'available'
                LIMIT 5
            """, (company_id,))
            rows = cursor.fetchall()
            if rows:
                value = ', '.join([row[0] for row in rows])
        
        elif source == 'experience':
            # Get recent project
            cursor.execute("""
                SELECT project_name FROM experience_record 
                WHERE company_id = ? AND is_completed = 1
                ORDER BY completion_date DESC
                LIMIT 1
            """, (company_id,))
            row = cursor.fetchone()
            if row:
                value = row[0]
        
        elif source == 'financial':
            # Get latest financial data
            if field == 'annual_turnover':
                cursor.execute("""
                    SELECT annual_turnover FROM financial_capacity 
                    WHERE company_id = ?
                    ORDER BY fiscal_year DESC
                    LIMIT 1
                """, (company_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    value = f"৳{row[0]:,.0f}"
        
        elif source == 'company_profile':
            # Get company info
            cursor.execute("""
                SELECT {} FROM companies WHERE id = ?
            """.format(field), (company_id,))
            row = cursor.fetchone()
            if row and row[0]:
                value = row[0]
        
        elif source == 'certificate':
            # Get certificate info
            if field == 'certificate_name':
                cursor.execute("""
                    SELECT certificate_name FROM certificate 
                    WHERE company_id = ? AND verification_status = 'approved'
                    LIMIT 1
                """, (company_id,))
                row = cursor.fetchone()
                if row:
                    value = row[0]
        
        conn.close()
        return value
        
    except Exception as e:
        logger.error(f"Error getting field value: {e}")
        return None


def search_company_data(company_id, query, categories=None):
    """Search across company data"""
    results = []
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        search_term = f"%{query}%"
        
        # Search personnel
        if not categories or 'personnel' in categories:
            cursor.execute("""
                SELECT 'personnel' as source, id, full_name as name, designation
                FROM personnel
                WHERE company_id = ? AND employment_status = 'active'
                AND (full_name LIKE ? OR designation LIKE ? OR skills LIKE ?)
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in cursor.fetchall():
                results.append({
                    'source': row[0],
                    'id': row[1],
                    'name': row[2],
                    'designation': row[3]
                })
        
        # Search equipment
        if not categories or 'equipment' in categories:
            cursor.execute("""
                SELECT 'equipment' as source, id, equipment_name as name, equipment_type
                FROM equipment
                WHERE company_id = ?
                AND (equipment_name LIKE ? OR model LIKE ? OR equipment_type LIKE ?)
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in cursor.fetchall():
                results.append({
                    'source': row[0],
                    'id': row[1],
                    'name': row[2],
                    'type': row[3]
                })
        
        # Search experiences
        if not categories or 'experience' in categories:
            cursor.execute("""
                SELECT 'experience' as source, id, project_name as name, client_name
                FROM experience_record
                WHERE company_id = ?
                AND (project_name LIKE ? OR client_name LIKE ? OR nature_of_work LIKE ?)
                ORDER BY completion_date DESC
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in cursor.fetchall():
                results.append({
                    'source': row[0],
                    'id': row[1],
                    'name': row[2],
                    'client': row[3]
                })
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Search error: {e}")
    
    return results