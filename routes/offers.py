from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.tarjous import Tarjous
from models.category import Category
from models.offer_analytics import OfferAnalytics
from datetime import datetime

# Create blueprint
offers_bp = Blueprint('offers', __name__)

# Note: Limiter will be passed from main app
limiter = None

def init_limiter(app_limiter):
    """Initialize limiter for this blueprint"""
    global limiter
    limiter = app_limiter

@offers_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories"""
    if limiter:
        limiter.limit("250 per hour")(get_categories)
    
    try:
        categories = Category.get_all_categories()
        return jsonify({
            'success': True,
            'data': {
                'categories': categories
            }
        })
    except Exception as e:
        print(f"Categories error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch categories'
        }), 500

@offers_bp.route('/tarjoukset/public', methods=['GET'])
def get_public_offers():
    """Get paginated offers - public endpoint for home screen"""
    if limiter:
        limiter.limit("400 per hour")(get_public_offers)
    
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        category = request.args.get('category')
        city = request.args.get('city')
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 50:
            limit = 20
        
        # Get offers
        result = Tarjous.get_offers(page=page, limit=limit, category=category, city=city)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"Get public offers error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch offers'
        }), 500

@offers_bp.route('/tarjoukset', methods=['GET'])
@jwt_required()
def get_offers():
    """Get paginated offers"""
    if limiter:
        limiter.limit("400 per hour")(get_offers)
    
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        category = request.args.get('category')
        city = request.args.get('city')
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 50:
            limit = 20
        
        # Get offers
        result = Tarjous.get_offers(page=page, limit=limit, category=category, city=city)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"Get offers error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch offers'
        }), 500

@offers_bp.route('/tarjoukset/search', methods=['GET'])
@jwt_required()
def search_offers():
    """Search offers"""
    try:
        # Get query parameters
        search_term = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Search term is required'
            }), 400
        
        # Validate parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 50:
            limit = 20
        
        # Search offers
        result = Tarjous.search_offers(search_term, page=page, limit=limit)
        
        return jsonify({
            'success': True,
            'data': result,
            'searchTerm': search_term
        })
        
    except Exception as e:
        print(f"Search offers error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to search offers'
        }), 500

@offers_bp.route('/tarjoukset/<offer_id>', methods=['GET'])
@jwt_required()
def get_offer_details(offer_id):
    """Get offer details by ID"""
    try:
        # Find offer by ID
        offer = Tarjous.find_by_id(offer_id)
        
        if not offer:
            return jsonify({
                'success': False,
                'message': 'Offer not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'offer': offer.to_dict()
            }
        })
        
    except Exception as e:
        print(f"Get offer details error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get offer details'
        }), 500

@offers_bp.route('/tarjoukset/<offer_id>/click', methods=['POST'])
@jwt_required()
def track_offer_click(offer_id):
    """Track offer click"""
    try:
        user_id = get_jwt_identity()
        
        # Verify offer exists
        offer = Tarjous.find_by_id(offer_id)
        if not offer:
            return jsonify({
                'success': False,
                'message': 'Offer not found'
            }), 404
        
        # Track click using the correct method
        OfferAnalytics.track_offer_interaction(
            offer_id=offer_id,
            user_id=user_id,
            event_type='click'
        )
        
        return jsonify({
            'success': True,
            'message': 'Click tracked successfully'
        })
        
    except Exception as e:
        print(f"Track click error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to track click'
        }), 500

@offers_bp.route('/tarjoukset/<offer_id>/conversion/website', methods=['POST'])
@jwt_required()
def track_website_conversion(offer_id):
    """Track website visit conversion"""
    try:
        user_id = get_jwt_identity()
        
        # Verify offer exists
        offer = Tarjous.find_by_id(offer_id)
        if not offer:
            return jsonify({
                'success': False,
                'message': 'Offer not found'
            }), 404
        
        # Track website conversion
        OfferAnalytics.track_conversion(
            offer_id=offer_id,
            conversion_type='website',
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Website conversion tracked successfully'
        })
        
    except Exception as e:
        print(f"Track website conversion error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to track website conversion'
        }), 500

@offers_bp.route('/tarjoukset/<offer_id>/conversion/call', methods=['POST'])
@jwt_required()
def track_call_conversion(offer_id):
    """Track phone call conversion"""
    try:
        user_id = get_jwt_identity()
        
        # Verify offer exists
        offer = Tarjous.find_by_id(offer_id)
        if not offer:
            return jsonify({
                'success': False,
                'message': 'Offer not found'
            }), 404
        
        # Track call conversion
        OfferAnalytics.track_conversion(
            offer_id=offer_id,
            conversion_type='call',
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Call conversion tracked successfully'
        })
        
    except Exception as e:
        print(f"Track call conversion error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to track call conversion'
        }), 500

@offers_bp.route('/tarjoukset/<offer_id>/conversion/directions', methods=['POST'])
@jwt_required()
def track_directions_conversion(offer_id):
    """Track directions request conversion"""
    try:
        user_id = get_jwt_identity()
        
        # Verify offer exists
        offer = Tarjous.find_by_id(offer_id)
        if not offer:
            return jsonify({
                'success': False,
                'message': 'Offer not found'
            }), 404
        
        # Track directions conversion
        OfferAnalytics.track_conversion(
            offer_id=offer_id,
            conversion_type='directions',
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Directions conversion tracked successfully'
        })
        
    except Exception as e:
        print(f"Track directions conversion error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to track directions conversion'
        }), 500 