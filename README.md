# Etuhinta Backend - Flask API

This is the Flask-based backend API for the Etuhinta mobile application, providing authentication, offers management, and analytics functionality.

## Features

- **Authentication**: JWT-based user registration and login
- **Offers Management**: CRUD operations for discount offers (tarjoukset)
- **Analytics**: Event tracking and dashboard analytics
- **Security**: Rate limiting, CORS, input validation, password hashing
- **Database**: PostgreSQL with connection pooling

## Tech Stack

- **Framework**: Flask 2.3.3
- **Database**: PostgreSQL with psycopg2
- **Authentication**: Flask-JWT-Extended with bcrypt
- **Security**: Flask-CORS, Flask-Limiter
- **Environment**: python-dotenv

## Installation

1. **Clone the repository and navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv etuhinta_env
   source etuhinta_env/bin/activate  # On Windows: etuhinta_env\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the backend directory:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=etuhinta_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   # JWT Configuration
   JWT_SECRET=your-super-secret-jwt-key-change-in-production
   
   # Server Configuration
   PORT=3001
   NODE_ENV=development
   ```

5. **Set up PostgreSQL database:**
   ```sql
   CREATE DATABASE etuhinta_db;
   CREATE USER etuhinta_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE etuhinta_db TO etuhinta_user;
   ```

6. **Initialize database and add sample data:**
   ```bash
   python check_db.py
   ```

## Running the Server

### Development
```bash
python app.py
```

### Production (with Gunicorn)
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:3001 --workers 4 app:app
```

The server will start on `http://localhost:3001`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile (requires JWT)
- `POST /api/auth/logout` - User logout (requires JWT)

### Offers (Tarjoukset)
- `GET /api/tarjoukset` - Get paginated offers (requires JWT)
- `GET /api/tarjoukset/search` - Search offers (requires JWT)
- `GET /api/tarjoukset/:id` - Get offer details (requires JWT)
- `POST /api/tarjoukset/:id/click` - Track offer click (requires JWT)

### Analytics
- `POST /api/analytics/track` - Track analytics event (requires JWT)
- `GET /api/analytics/dashboard` - Get dashboard data (requires JWT)

### Health Check
- `GET /health` - Server health check

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    date_of_birth DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Tarjoukset (Offers) Table
```sql
CREATE TABLE tarjoukset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    original_price DECIMAL(10,2),
    discount_price DECIMAL(10,2),
    discount_percentage INTEGER,
    image_url TEXT,
    category_name VARCHAR(100),
    merchant_name VARCHAR(255) NOT NULL,
    merchant_address TEXT,
    merchant_phone VARCHAR(50),
    merchant_website TEXT,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    terms TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Analytics Tables
```sql
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    tarjous_id UUID REFERENCES tarjoukset(id),
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE analytics_daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_views INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    top_categories JSONB,
    top_merchants JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Request/Response Examples

### User Registration
```bash
curl -X POST http://localhost:3001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Anna",
    "lastName": "Virtanen",
    "email": "anna@example.com",
    "password": "securepassword123"
  }'
```

### User Login
```bash
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "anna@example.com",
    "password": "securepassword123"
  }'
```

### Get Offers
```bash
curl -X GET "http://localhost:3001/api/tarjoukset?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Error Handling

The API returns standardized error responses:

```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Detailed error information"]
}
```

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt with salt rounds
- **Rate Limiting**: Prevents abuse and DoS attacks
- **CORS**: Configured for specific origins
- **Input Validation**: Server-side validation for all inputs
- **SQL Injection Protection**: Parameterized queries

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest
```

### Database Migrations
For database schema changes, update the model files and run:
```bash
python check_db.py
```

### Debugging
Set `debug=True` in `app.py` for development mode with detailed error messages.

## Deployment

1. **Environment Variables**: Set production environment variables
2. **Database**: Set up production PostgreSQL database
3. **WSGI Server**: Use Gunicorn or similar WSGI server
4. **Reverse Proxy**: Configure Nginx or Apache
5. **SSL**: Enable HTTPS for production

## License

This project is licensed under the MIT License. 