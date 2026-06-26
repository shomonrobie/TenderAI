# api/flask_api.py - Flask API Module for Extension
import logging

logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask').setLevel(logging.ERROR)

# Optional: Also suppress urllib3 logs
logging.getLogger('urllib3').setLevel(logging.WARNING)


from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import jwt
import os
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# JWT Secret (use environment variable in production)
JWT_SECRET = os.environ.get('JWT_SECRET', 'tenderai-secret-key-2024')

# Global reference to database (will be set when initializing)
_db = None

def init_flask_api(db):
    """Initialize Flask API with database reference"""
    global _db
    _db = db
    return create_flask_app()

def create_flask_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # ========== HEALTH CHECK ==========
    @app.route('/api/health', methods=['GET', 'HEAD'])
    def health_check():
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }), 200
    
    # ========== AUTHENTICATION ==========
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
           
            print("=" * 50)
            print("🔐 LOGIN REQUEST RECEIVED")
            print(f"Request headers: {dict(request.headers)}")
            print(f"Request data: {request.get_data()}")
            
            data = request.get_json()
            print(f"Parsed JSON: {data}")
            
            username = data.get('username')
            password = data.get('password')
            
            print(f"Username: {username}")
            
            if not username or not password:
                print("❌ Missing username or password")
                return jsonify({'success': False, 'message': 'Username and password required'}), 400
            
            user, status, message = _db.authenticate_user(username, password)
            
            print(f"Auth result - user: {user is not None}, status: {status}, message: {message}")
            
            if not user:
                print(f"❌ Authentication failed: {message}")
                return jsonify({'success': False, 'message': message or 'Invalid credentials'}), 401
            
            print("✅ Authentication successful")
            print("=" * 50)
            
            
            user, status, message = _db.authenticate_user(username, password)
            
            if not user:
                return jsonify({'success': False, 'message': message or 'Invalid credentials'}), 401
            
            # Check if user is approved
            is_approved = user[9] if len(user) > 9 else 1
            if not is_approved:
                return jsonify({'success': False, 'message': 'Account pending approval'}), 403
            
            # Check if user is active
            is_active = user[8] if len(user) > 8 else 1
            if not is_active:
                return jsonify({'success': False, 'message': 'Account is deactivated'}), 403
            
            # Get subscription info
            #subscription = _db.get_user_subscription(user[0])
            subscription = db.get_user_subscription(user.get('id'))

            plan = subscription.get('plan', 'free')
            
            # Check if user is already logged in the main app
            is_logged_in_main = check_main_app_session(username)
            
            token = jwt.encode({
                'user_id': user[0],
                'company_id': user[6],
                'role': user[4],
                'username': user[1],
                'email': user[2],
                'plan': plan,
                'is_logged_in_main': is_logged_in_main,
                'exp': datetime.utcnow() + timedelta(hours=24)
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
                    'plan': plan,
                    'is_logged_in_main': is_logged_in_main
                }
            })
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/check-session', methods=['GET'])
    def check_session():
        """Check if user has active session in main app"""
        try:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'is_logged_in': False}), 401
            
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                username = payload.get('username')
                
                is_logged_in = check_main_app_session(username)
                return jsonify({'is_logged_in': is_logged_in, 'username': username})
            except:
                return jsonify({'is_logged_in': False}), 401
        except Exception as e:
            return jsonify({'is_logged_in': False}), 500
    
    # ========== FIELD MATCHING ==========
    @app.route('/api/match-field', methods=['POST'])
    def match_field():
        try:
            data = request.get_json()
            label = data.get('label', '')
            field_type = data.get('fieldType', 'text')
            
            label_lower = label.lower()
            
            # Comprehensive field matching patterns
            field_patterns = {
                'company_name': {
                    'keywords': ['company', 'firm', 'organization', 'contractor', 'name of firm', 'bidder name'],
                    'source': 'company_profile',
                    'field': 'company_name',
                    'confidence': 0.85
                },
                'tin_number': {
                    'keywords': ['tin', 'tax identification', 'tax id', 'tin number'],
                    'source': 'company_profile',
                    'field': 'tin_number',
                    'confidence': 0.90
                },
                'vat_number': {
                    'keywords': ['vat', 'value added tax', 'vat number', 'registration number'],
                    'source': 'company_profile',
                    'field': 'vat_number',
                    'confidence': 0.90
                },
                'phone': {
                    'keywords': ['phone', 'mobile', 'contact number', 'telephone', 'cell'],
                    'source': 'company_profile',
                    'field': 'phone',
                    'confidence': 0.85
                },
                'email': {
                    'keywords': ['email', 'e-mail', 'electronic mail'],
                    'source': 'company_profile',
                    'field': 'email',
                    'confidence': 0.95
                },
                'address': {
                    'keywords': ['address', 'office address', 'registered address', 'principal address'],
                    'source': 'company_profile',
                    'field': 'address',
                    'confidence': 0.80
                },
                'registration_number': {
                    'keywords': ['registration', 'reg no', 'registration number', 'rc no'],
                    'source': 'company_profile',
                    'field': 'registration_number',
                    'confidence': 0.85
                }
            }
            
            for field_name, pattern in field_patterns.items():
                for keyword in pattern['keywords']:
                    if keyword in label_lower:
                        return jsonify({
                            'match': {
                                'source': pattern['source'],
                                'field': pattern['field'],
                                'confidence': pattern['confidence']
                            }
                        })
            
            return jsonify({'match': None})
            
        except Exception as e:
            logger.error(f"Match field error: {e}")
            return jsonify({'match': None}), 500
    
    @app.route('/api/get-fill-value', methods=['POST'])
    def get_fill_value():
        try:
            data = request.get_json()
            source = data.get('source')
            field = data.get('field')
            
            # Get auth token from header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'value': None}), 401
            
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                company_id = payload['company_id']
            except:
                return jsonify({'value': None}), 401
            
            conn = _db.get_connection()
            cursor = conn.cursor()
            value = None
            
            if source == 'company_profile':
                cursor.execute(f"SELECT {field} FROM companies WHERE id = ?", (company_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    value = row[0]
            
            conn.close()
            return jsonify({'value': value})
            
        except Exception as e:
            logger.error(f"Get fill value error: {e}")
            return jsonify({'value': None}), 500
    
    # ========== AUTO-FILL DATA ==========
    @app.route('/api/auto-fill/<data_type>', methods=['GET'])
    def get_auto_fill_data(data_type):
        try:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({}), 401
            
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                company_id = payload['company_id']
            except:
                return jsonify({}), 401
            
            conn = _db.get_connection()
            cursor = conn.cursor()
            result = {}
            
            if data_type == 'company':
                cursor.execute("""
                    SELECT company_name, email, phone, address, registration_number, vat_number
                    FROM companies WHERE id = ?
                """, (company_id,))
                row = cursor.fetchone()
                if row:
                    result['company'] = {
                        'name': row[0],
                        'email': row[1],
                        'phone': row[2],
                        'address': row[3],
                        'registration_number': row[4],
                        'vat_number': row[5]
                    }
            
            elif data_type == 'personnel':
                cursor.execute("""
                    SELECT id, full_name, designation, employee_id, skills
                    FROM personnel WHERE company_id = ? AND employment_status = 'active'
                    ORDER BY is_key_personnel DESC LIMIT 20
                """, (company_id,))
                personnel = []
                for row in cursor.fetchall():
                    personnel.append({
                        'id': row[0], 'name': row[1], 'designation': row[2],
                        'employee_id': row[3], 'skills': row[4]
                    })
                result['personnel'] = personnel
            
            conn.close()
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Auto-fill error: {e}")
            return jsonify({}), 500
    
    @app.route('/api/track/form-fill', methods=['POST'])
    def track_form_fill():
        try:
            data = request.get_json()
            
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'success': False}), 401
            
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                company_id = payload['company_id']
                user_id = payload['user_id']
            except:
                return jsonify({'success': False}), 401
            
            conn = _db.get_connection()
            cursor = conn.cursor()
                    
            
            cursor.execute("""
                INSERT INTO extension_auto_fill_log 
                (company_id, user_id, field_label, confidence_score, page_url, filled_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                company_id, user_id,
                data.get('field_label', ''),
                data.get('confidence', 0),
                data.get('url', ''),
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Track error: {e}")
            return jsonify({'success': False}), 500

    
    @app.route('/api/usage/stats', methods=['GET'])
    def get_usage_stats():
        try:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'usage': {'used': 0, 'limit': 5, 'remaining': 5}}), 401
            
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                company_id = payload['company_id']
            except:
                return jsonify({'usage': {'used': 0, 'limit': 5, 'remaining': 5}}), 401
            
            this_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            conn = _db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM extension_auto_fill_log WHERE company_id = ? AND filled_at >= ?", (company_id, this_month))
            used = cursor.fetchone()[0] or 0
            conn.close()
            
            sub = _db.get_company_subscription(company_id)
            plan = sub.get('plan', 'free')
            plan_limits = {'free': 5, 'basic': 30, 'professional': 100, 'enterprise': -1}
            limit = plan_limits.get(plan, 5)
            
            return jsonify({
                'usage': {
                    'used': used, 'limit': limit,
                    'remaining': -1 if limit == -1 else max(0, limit - used),
                    'is_unlimited': limit == -1
                }
            })
        except Exception as e:
            return jsonify({'usage': {'used': 0, 'limit': 5, 'remaining': 5}}), 500
    
    return app


def check_main_app_session(username):
    """Check if user has active session in main Streamlit app"""
    # This is a simplified check - in production, use Redis or database
    # For now, we'll return True if the user is the current session user
    try:
        import streamlit as st
        if st.session_state.get('logged_in') and st.session_state.get('username') == username:
            return True
    except:
        pass
    return False


# Flask server thread management
_flask_thread = None
_flask_started = False

def start_flask_api(db, port=5000):
    """Start Flask API in background thread"""
    global _flask_thread, _flask_started
    
    if _flask_started:
        print("Flask API already running")
        return
    
    app = init_flask_api(db)
    
    def run():
        try:
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"Flask API error: {e}")
    
    _flask_thread = threading.Thread(target=run, daemon=True)
    _flask_thread.start()
    _flask_started = True
    print(f"✅ Flask API started on port {port}")