from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.analytics import Analytics
from models.simple_analytics import SimpleAnalytics
from models.offer_analytics import OfferAnalytics
from datetime import datetime, timedelta

# Create blueprint
analytics_bp = Blueprint('analytics', __name__)

# Note: Limiter will be passed from main app
limiter = None

def init_limiter(app_limiter):
    """Initialize limiter for this blueprint"""
    global limiter
    limiter = app_limiter

@analytics_bp.route('/analytics/track', methods=['POST'])
@jwt_required()
def track_analytics():
    """Track analytics event"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Handle both old and new data formats
        event_type = data.get('event_type') or data.get('eventType', 'unknown')
        page = data.get('page', 'unknown')  # Make page optional with default
        
        # Prepare analytics data with backward compatibility
        analytics_data = {
            'user_id': user_id,
            'event_type': event_type,
            'page': page,
            'offer_id': data.get('offer_id') or data.get('tarjousId') or data.get('offerId'),
            'category': data.get('category'),
            'search_term': data.get('search_term'),
            'city': data.get('city') or (data.get('data', {}).get('city') if isinstance(data.get('data'), dict) else None),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'referrer': request.headers.get('Referer', ''),
            'session_duration': data.get('session_duration'),
            'metadata': data.get('metadata') or data.get('data', {})
        }
        
        # Track the event with individual parameters
        Analytics.track_event(
            event_type=analytics_data['event_type'],
            session_id=request.headers.get('x-session-id', 'unknown'),
            user_id=analytics_data['user_id'],
            offer_id=analytics_data['offer_id'],
            metadata=analytics_data['metadata'],
            ip_address=analytics_data['ip_address'],
            user_agent=analytics_data['user_agent']
        )
        
        return jsonify({
            'success': True,
            'message': 'Analytics event tracked successfully'
        })
        
    except Exception as e:
        print(f"Track analytics error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to track analytics'
        }), 500

@analytics_bp.route('/analytics/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    """Get dashboard analytics data"""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get analytics data
        dashboard_data = Analytics.get_dashboard_data(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        print(f"Get dashboard data error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get dashboard data'
        }), 500

@analytics_bp.route('/analytics/location', methods=['GET'])
@jwt_required()
def get_location_analytics():
    """Get location-based analytics"""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get location analytics
        location_data = Analytics.get_location_analytics(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': location_data
        })
        
    except Exception as e:
        print(f"Get location analytics error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get location analytics'
        }), 500

@analytics_bp.route('/analytics/offers/<int:offer_id>/location', methods=['GET'])
@jwt_required()
def get_offer_location_analytics(offer_id):
    """Get location analytics for specific offer"""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get offer location analytics
        location_data = OfferAnalytics.get_offer_location_analytics(offer_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': location_data
        })
        
    except Exception as e:
        print(f"Get offer location analytics error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get offer location analytics'
        }), 500

@analytics_bp.route('/analytics/cities', methods=['GET'])
@jwt_required()
def get_city_analytics():
    """Get city-based analytics"""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get city analytics
        city_data = Analytics.get_city_analytics(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': city_data
        })
        
    except Exception as e:
        print(f"Get city analytics error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get city analytics'
        }), 500 