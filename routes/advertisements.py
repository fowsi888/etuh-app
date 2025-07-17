from flask import Blueprint, request, jsonify
from models.advertisement import Advertisement
import traceback

advertisements_bp = Blueprint('advertisements', __name__)

@advertisements_bp.route('/advertisements/active', methods=['GET'])
def get_active_advertisements():
    """Get active advertisements for display"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 6, type=int)
        
        # Validate limit (max 20 for performance)
        if limit > 20:
            limit = 20
        
        # Get active ads
        ads = Advertisement.get_active_ads(limit=limit)
        
        return jsonify({
            'success': True,
            'ads': ads,
            'count': len(ads)
        }), 200
        
    except Exception as error:
        print(f'❌ Error in get_active_advertisements: {error}')
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Failed to get advertisements'
        }), 500

@advertisements_bp.route('/advertisements/<int:ad_id>/click', methods=['POST'])
def track_click(ad_id):
    """Track a click for an advertisement"""
    try:
        success = Advertisement.track_click(ad_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Click tracked successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to track click'
            }), 400
            
    except Exception as error:
        print(f'❌ Error in track_click: {error}')
        return jsonify({
            'success': False,
            'message': 'Failed to track click'
        }), 500

@advertisements_bp.route('/advertisements/<int:ad_id>', methods=['GET'])
def get_advertisement(ad_id):
    """Get a specific advertisement by ID"""
    try:
        ad = Advertisement.find_by_id(ad_id)
        
        if not ad:
            return jsonify({
                'success': False,
                'message': 'Advertisement not found'
            }), 404
        
        return jsonify({
            'success': True,
            'ad': ad.to_dict()
        }), 200
        
    except Exception as error:
        print(f'❌ Error in get_advertisement: {error}')
        return jsonify({
            'success': False,
            'message': 'Failed to get advertisement'
        }), 500

@advertisements_bp.route('/advertisements/stats', methods=['GET'])
def get_advertisement_stats():
    """Get simple advertisement statistics"""
    try:
        stats = Advertisement.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as error:
        print(f'❌ Error in get_advertisement_stats: {error}')
        return jsonify({
            'success': False,
            'message': 'Failed to get advertisement statistics'
        }), 500 