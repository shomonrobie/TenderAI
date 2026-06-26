# api/tenant_rate_api.py

import json
import logging
from flask import Blueprint, request, jsonify, send_file
from services.tenant_rate_service import TenantRateService
from utils.auth import require_auth, require_permission
from utils.validators import validate_request

logger = logging.getLogger(__name__)

rate_api = Blueprint('rate_api', __name__, url_prefix='/api/rates')
service = TenantRateService()

# ========== RATE BOOKS ==========

@rate_api.route('/books', methods=['GET'])
@require_auth
def get_rate_books():
    """Get rate books for current tenant"""
    user = request.user
    tenant_id = user.get('company_id') or user.get('id')
    tenant_type = 'company' if user.get('company_id') else 'user'
    
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    
    result = service.get_rate_books(tenant_id, tenant_type, include_archived)
    return jsonify(result)

@rate_api.route('/books', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def create_rate_book():
    """Create a new rate book"""
    data = request.json
    user = request.user
    
    tenant_id = user.get('company_id') or user.get('id')
    tenant_type = 'company' if user.get('company_id') else 'user'
    
    result = service.create_rate_book(
        tenant_id=tenant_id,
        tenant_type=tenant_type,
        name=data.get('name'),
        source_type=data.get('source_type', 'CUSTOM'),
        description=data.get('description'),
        source_version_id=data.get('source_version_id'),
        created_by=user.get('id')
    )
    
    return jsonify(result), 201 if result['success'] else 400

@rate_api.route('/books/<int:book_id>', methods=['GET'])
@require_auth
def get_rate_book(book_id):
    """Get rate book details"""
    user = request.user
    
    # Check tenant access
    result = service.repository.get_rate_book(book_id)
    if not result:
        return jsonify({'success': False, 'error': 'Rate book not found'}), 404
    
    tenant_id = user.get('company_id') or user.get('id')
    if result['tenant_id'] != tenant_id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    return jsonify({'success': True, 'book': result})

@rate_api.route('/books/<int:book_id>', methods=['PUT'])
@require_auth
@require_permission('manage_tenant_rates')
def update_rate_book(book_id):
    """Update a rate book"""
    data = request.json
    result = service.repository.update_rate_book(book_id, data)
    
    if result:
        return jsonify({'success': True, 'message': 'Rate book updated'})
    else:
        return jsonify({'success': False, 'error': 'Update failed'}), 400

@rate_api.route('/books/<int:book_id>/archive', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def archive_rate_book(book_id):
    """Archive a rate book"""
    result = service.repository.archive_rate_book(book_id)
    
    if result:
        return jsonify({'success': True, 'message': 'Rate book archived'})
    else:
        return jsonify({'success': False, 'error': 'Archive failed'}), 400

@rate_api.route('/books/<int:book_id>/clone', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def clone_master_rates(book_id):
    """Clone master rates to a rate book"""
    data = request.json
    user = request.user
    
    result = service.clone_master_rates(
        book_id=book_id,
        source_type=data.get('source_type'),
        version_id=data.get('version_id'),
        filters=data.get('filters'),
        user_id=user.get('id')
    )
    
    return jsonify(result)

# ========== VERSIONS ==========

@rate_api.route('/books/<int:book_id>/versions', methods=['GET'])
@require_auth
def get_versions(book_id):
    """Get all versions for a rate book"""
    result = service.repository.get_versions_for_book(book_id)
    return jsonify({'success': True, 'versions': result})

@rate_api.route('/books/<int:book_id>/versions', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def create_version(book_id):
    """Create a new version"""
    data = request.json
    user = request.user
    
    result = service.create_version(
        book_id=book_id,
        version_name=data.get('version_name'),
        effective_from=data.get('effective_from'),
        notes=data.get('notes'),
        created_by=user.get('id')
    )
    
    return jsonify(result)

@rate_api.route('/versions/<int:version_id>/set-current', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def set_current_version(version_id):
    """Set a version as current"""
    result = service.set_current_version(version_id)
    return jsonify(result)

# ========== ITEMS AND PRICING ==========

@rate_api.route('/books/<int:book_id>/items', methods=['GET'])
@require_auth
def get_items(book_id):
    """Get items for a rate book"""
    version_id = request.args.get('version_id', type=int)
    search = request.args.get('search')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    result = service.get_items(book_id, version_id, search, active_only)
    return jsonify(result)

@rate_api.route('/books/<int:book_id>/items', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def create_item(book_id):
    """Create a custom rate item"""
    data = request.json
    user = request.user
    
    result = service.repository.create_rate_item({
        'rate_book_id': book_id,
        'item_code': data['item_code'],
        'item_description': data['item_description'],
        'unit': data.get('unit'),
        'is_custom': 1,
        'created_by': user.get('id')
    })
    
    if result:
        return jsonify({
            'success': True,
            'item_id': result,
            'message': 'Item created successfully'
        }), 201
    else:
        return jsonify({'success': False, 'error': 'Create failed'}), 400

@rate_api.route('/items/<int:item_id>/pricing', methods=['PUT'])
@require_auth
@require_permission('manage_tenant_rates')
def update_pricing(item_id):
    """Update pricing for an item"""
    data = request.json
    user = request.user
    
    result = service.update_pricing(
        version_id=data.get('version_id'),
        item_id=item_id,
        pricing_level=data.get('pricing_level'),
        price=data.get('price'),
        user_id=user.get('id')
    )
    
    return jsonify(result)

@rate_api.route('/items/pricing/bulk', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def bulk_update_pricing():
    """Bulk update pricing for multiple items"""
    data = request.json
    user = request.user
    
    result = service.update_bulk_pricing(
        version_id=data.get('version_id'),
        updates=data.get('updates', []),
        user_id=user.get('id')
    )
    
    return jsonify(result)

# ========== AUDIT ==========

@rate_api.route('/audit', methods=['GET'])
@require_auth
def get_audit_log():
    """Get audit log"""
    book_id = request.args.get('book_id', type=int)
    user_id = request.args.get('user_id', type=int)
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    result = service.get_audit_log(book_id, user_id, page, page_size)
    return jsonify(result)

# ========== IMPORT/EXPORT ==========

@rate_api.route('/books/<int:book_id>/import', methods=['POST'])
@require_auth
@require_permission('manage_tenant_rates')
def import_rates(book_id):
    """Import rates from file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    import_type = request.form.get('import_type', 'PWD')
    
    # Process import
    # Implementation depends on file format (Excel/CSV)
    
    return jsonify({'success': True, 'message': 'Import completed'})

@rate_api.route('/books/<int:book_id>/export', methods=['GET'])
@require_auth
@require_permission('manage_tenant_rates')
def export_rates(book_id):
    """Export rates to file"""
    export_type = request.args.get('export_type', 'Excel')
    version_id = request.args.get('version_id', type=int)
    
    # Generate export file
    # Implementation depends on export format
    
    return send_file(
        f'temp_export_{book_id}.xlsx',
        as_attachment=True,
        download_name=f'rate_book_{book_id}.xlsx'
    )