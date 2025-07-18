from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config.database import init_db

# Import blueprints
from routes.advertisements import advertisements_bp
from routes.auth import auth_bp, init_limiter as init_auth_limiter
from routes.offers import offers_bp, init_limiter as init_offers_limiter
from routes.analytics import analytics_bp, init_limiter as init_analytics_limiter
from routes.ai_chat import ai_chat_bp, init_limiter as init_ai_chat_limiter

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Initialize extensions
jwt = JWTManager(app)
CORS(app, 
     origins=['http://172.20.10.3:8080', 'http://localhost:8080', 'http://localhost:3000', '*'],  # Allow specific origins including IP
     allow_headers=['Content-Type', 'Authorization', 'x-session-id'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     supports_credentials=False)  # Set to False when using origins='*'

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["3000 per day", "400 per hour"]  # Increased for more users
)

# Initialize limiter for blueprints
init_auth_limiter(limiter)
init_offers_limiter(limiter)
init_analytics_limiter(limiter)
init_ai_chat_limiter(limiter)

# Register blueprints
app.register_blueprint(advertisements_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(offers_bp, url_prefix='/api')
app.register_blueprint(analytics_bp, url_prefix='/api')
app.register_blueprint(ai_chat_bp, url_prefix='/api')

# Static file serving for uploads
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    return send_from_directory(uploads_dir, filename)

# Add request logging for debugging
@app.before_request
def log_request_info():
    print(f"🔍 {request.method} {request.url}")
    # Only log essential info, not full headers
    if request.headers.get('Origin'):
        print(f"🌐 Origin: {request.headers.get('Origin')}")
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        try:
            json_data = request.get_json()
            if json_data:
                # Only log non-sensitive data
                safe_data = {k: v for k, v in json_data.items() if k not in ['password', 'confirmPassword', 'token']}
                print(f"📋 JSON Data: {safe_data}")
        except Exception as json_error:
            print(f"❌ JSON parsing error: {json_error}")
    print("---")

# Initialize database
init_db()

# Update database schema for password reset functionality
try:
    from models.user import User
    User.update_database_schema()
except Exception as e:
    print(f"⚠️ Warning: Could not update database schema: {e}")

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'message': 'Bad request',
        'errors': [str(error)]
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'message': 'Unauthorized access',
        'errors': [str(error)]
    }), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Resource not found',
        'errors': [str(error)]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error',
        'errors': [str(error)]
    }), 500

@app.errorhandler(422)
def unprocessable_entity(error):
    print(f"🚨 422 Error occurred: {error}")
    return jsonify({
        'success': False,
        'message': 'Unprocessable entity - validation error',
        'errors': [str(error)]
    }), 422

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'message': 'Server is running',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development' or os.getenv('NODE_ENV') == 'development'
    
    print(f"🚀 Server starting on port {port}")
    print(f"📊 Environment: {os.getenv('NODE_ENV', 'development')}")
    print(f"🔗 Database: {os.getenv('DB_NAME', 'etuhinta')}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 