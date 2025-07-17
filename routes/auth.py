from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.user import User
import bcrypt

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Note: Limiter will be passed from main app
limiter = None

def init_limiter(app_limiter):
    """Initialize limiter for this blueprint"""
    global limiter
    limiter = app_limiter

@auth_bp.route('/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    if limiter:
        limiter.limit("5 per minute")(register)
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        required_fields = ['email', 'password', 'firstName', 'lastName', 'city']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate password confirmation if provided
        if 'confirmPassword' in data:
            if data['password'] != data['confirmPassword']:
                return jsonify({
                    'success': False,
                    'message': 'Passwords do not match'
                }), 400
        
        # Register user (including city)
        user_data = {
            'email': data['email'],
            'password': data['password'],
            'firstName': data['firstName'],
            'lastName': data['lastName'],
            'city': data['city']
        }
        user = User.register(user_data)
        
        # Create JWT token with string identity
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'user': user.to_dict(),
                'token': access_token
            }
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'message': 'Registration failed'
        }), 500

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    if limiter:
        limiter.limit("10 per minute")(login)
    
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        # Authenticate user
        user = User.authenticate(data['email'], data['password'])
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        # Create JWT token with string identity
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': user.to_dict(),
                'token': access_token
            }
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed'
        }), 500

@auth_bp.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'user': user.to_dict()
            }
        })
        
    except Exception as e:
        print(f"Get profile error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get profile'
        }), 500

@auth_bp.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # First get the user instance
        user = User.find_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Update user profile using instance method
        updated_user = user.update_profile(data)
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {
                'user': updated_user.to_dict()
            }
        })
        
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update profile'
        }), 500

@auth_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    if limiter:
        limiter.limit("5 per hour")(change_password)
    
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('currentPassword') or not data.get('newPassword'):
            return jsonify({
                'success': False,
                'message': 'Current password and new password are required'
            }), 400
        
        current_password = data['currentPassword'].strip()
        new_password = data['newPassword'].strip()
        
        # Validate new password length
        if len(new_password) < 6:
            return jsonify({
                'success': False,
                'message': 'New password must be at least 6 characters long'
            }), 400
        
        # Get user and verify current password
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if not user.verify_password(current_password):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 401
        
        # Check if new password is different from current
        if user.verify_password(new_password):
            return jsonify({
                'success': False,
                'message': 'New password must be different from current password'
            }), 400
        
        # Change password
        success = user.change_password(new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to change password'
            }), 500
        
    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to change password'
        }), 500

@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint"""
    try:
        # Try to get JSON data, but don't require it
        data = request.get_json() if request.is_json else None
        # Logout successful regardless of whether there's a request body
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
    except Exception as e:
        # Even if there's an error, logout should succeed
        print(f"Logout warning (non-critical): {e}")
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })

@auth_bp.route('/auth/update-city', methods=['PUT'])
@jwt_required()
def update_city():
    """Update user city"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('city'):
            return jsonify({
                'success': False,
                'message': 'City is required'
            }), 400
        
        # First get the user instance
        user = User.find_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Update user city using instance method
        success = user.update_city(data['city'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'City updated successfully',
                'data': {
                    'user': user.to_dict()
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update city'
            }), 500
        
    except Exception as e:
        print(f"Update city error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update city'
        }), 500

@auth_bp.route('/auth/delete-account', methods=['DELETE'])
@jwt_required()
def delete_account():
    """Delete user account"""
    if limiter:
        limiter.limit("3 per hour")(delete_account)
    
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'Password confirmation required'
            }), 400
        
        # Verify password before deletion
        user = User.find_by_id(user_id)
        if not user or not user.verify_password(data['password']):
            return jsonify({
                'success': False,
                'message': 'Invalid password'
            }), 401
        
        # Delete user account
        success = User.delete_user(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Account deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete account'
            }), 500
        
    except Exception as e:
        print(f"Delete account error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete account'
        }), 500

@auth_bp.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Send temporary password email"""
    if limiter:
        limiter.limit("3 per 10 minutes")(forgot_password)
    
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        email = data['email'].strip().lower()
        
        # Create temporary password
        temp_password = User.create_password_reset_token(email)
        
        if not temp_password:
            # Don't reveal if email exists or not for security
            return jsonify({
                'success': True,
                'message': 'If the email exists, a temporary password has been sent'
            })
        
        # Send email
        from utils.email import send_password_reset_email
        email_sent = send_password_reset_email(email, temp_password)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'A temporary password has been sent to your email. Please log in with it and change your password immediately.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send temporary password email. Please try again later.'
            }), 500
            
    except Exception as e:
        print(f"Forgot password error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to process password reset request'
        }), 500 