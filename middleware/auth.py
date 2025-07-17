from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User

def require_auth(f):
    """Decorator to require authentication for a route"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from JWT token
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            # Add user_id to request for use in the route
            request.user_id = int(user_id)
            
            return f(*args, **kwargs)
        except Exception as e:
            print(f"❌ Auth middleware error: {e}")
            return jsonify({
                'success': False,
                'message': 'Authentication failed'
            }), 401
    
    return decorated_function

def require_admin(f):
    """Decorator to require admin authentication for a route"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            # Get user ID from JWT token
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            # Check if user exists and is admin
            user = User.find_by_id(int(user_id))
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 401
            
            # Check if user is admin (assuming there's an is_admin field)
            # For now, we'll allow all authenticated users as admin
            # You can modify this logic based on your user model
            if not getattr(user, 'is_admin', True):  # Default to True for now
                return jsonify({
                    'success': False,
                    'message': 'Admin access required'
                }), 403
            
            # Add user_id to request for use in the route
            request.user_id = int(user_id)
            request.user = user
            
            return f(*args, **kwargs)
        except Exception as e:
            print(f"❌ Admin auth middleware error: {e}")
            return jsonify({
                'success': False,
                'message': 'Authentication failed'
            }), 401
    
    return decorated_function 