from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.ai_chat import AIChat
from models.user import User
from datetime import datetime

# Create blueprint
ai_chat_bp = Blueprint('ai_chat', __name__)

# Note: Limiter will be passed from main app
limiter = None

def init_limiter(app_limiter):
    """Initialize limiter for this blueprint"""
    global limiter
    limiter = app_limiter

@ai_chat_bp.route('/ai-chat', methods=['POST'])
@jwt_required()
def ai_chat():
    """AI chat endpoint"""
    if limiter:
        limiter.limit("30 per minute")(ai_chat)
    
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        print(f"📋 JSON Data: {data}")
        
        if not data or not data.get('message'):
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Message cannot be empty'
            }), 400
        
        # Validate character limit (150 characters max)
        if len(user_message) > 150:
            return jsonify({
                'success': False,
                'message': f'Message too long. Maximum 150 characters allowed. Your message has {len(user_message)} characters.'
            }), 400
        
        # Create AIChat instance to get dynamic chat limit
        ai_chat_instance = AIChat()
        dynamic_chat_limit = ai_chat_instance.get_chat_limit()
        
        # Check if user has exceeded daily limit using dynamic limit
        if not User.check_ai_chat_limit(user_id, daily_limit=dynamic_chat_limit):
            return jsonify({
                'success': False,
                'message': f'Daily chat limit exceeded ({dynamic_chat_limit} messages per day). Please try again tomorrow.',
                'dailyLimit': dynamic_chat_limit,
                'limitReached': True
            }), 429
        
        # Get user city and language from request
        user_city = data.get('userCity', 'Helsinki')
        language = data.get('language', 'fi')
        
        # Process chat message
        response = ai_chat_instance.process_chat_message(
            user_message=user_message,
            user_city=user_city,
            language=language
        )
        
        if not response.get('success'):
            return jsonify({
                'success': False,
                'message': response.get('message', 'Failed to generate AI response')
            }), 500
        
        # Increment user's AI chat usage (only counts user inputs, not AI responses)
        print(f"📊 Incrementing chat usage for user {user_id} - this counts ONLY user input, not AI response")
        current_usage = User.increment_ai_chat_usage(user_id)
        print(f"📊 New usage count: {current_usage}/{dynamic_chat_limit}")
        
        return jsonify({
            'success': True,
            'message': response.get('message'),
            'offers': response.get('offers', []),
            'timestamp': datetime.now().isoformat(),
            'currentUsage': current_usage,
            'dailyLimit': dynamic_chat_limit,
            'limitReached': current_usage >= dynamic_chat_limit
        })
        
    except Exception as e:
        print(f"AI chat error: {e}")
        return jsonify({
            'success': False,
            'message': 'AI chat service temporarily unavailable'
        }), 500

@ai_chat_bp.route('/chat/usage', methods=['GET'])
@jwt_required()
def get_ai_chat_usage():
    """Get AI chat usage statistics"""
    try:
        user_id = get_jwt_identity()
        
        # Get dynamic chat limit from AIChat instance
        ai_chat_instance = AIChat()
        dynamic_chat_limit = ai_chat_instance.get_chat_limit()
        
        # Get usage statistics from User model
        usage_data = User.get_ai_chat_usage(user_id)
        daily_usage = usage_data.get('current_usage', 0)
        
        return jsonify({
            'success': True,
            'data': {
                'daily_usage': daily_usage,
                'daily_limit': dynamic_chat_limit,
                'remaining_today': max(0, dynamic_chat_limit - daily_usage),
                'date': usage_data.get('date'),
                'limitReached': daily_usage >= dynamic_chat_limit
            }
        })
        
    except Exception as e:
        print(f"Get AI chat usage error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get usage statistics'
        }), 500 