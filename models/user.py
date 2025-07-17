import bcrypt
from datetime import datetime
from config.database import execute_query, execute_query_dict, get_db_connection
import psycopg2.extras

class User:
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.first_name = user_data.get('firstname') or user_data.get('first_name')
        self.last_name = user_data.get('lastname') or user_data.get('last_name')
        self.city = user_data.get('city')
        self.phone_number = user_data.get('phone_number')
        self.date_of_birth = user_data.get('date_of_birth')
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self.is_active = user_data.get('is_active', True)

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'city': self.city,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLogin': self.last_login.isoformat() if self.last_login else None,
            'isActive': self.is_active
        }

    @staticmethod
    def create_table():
        """Create user table if not exists"""
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            city VARCHAR(100),
            phone_number VARCHAR(20),
            date_of_birth DATE,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_city ON users(city);
        
        -- Add AI chat usage columns to existing users table
        ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_chat_count INTEGER DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_chat_date DATE DEFAULT NULL;
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            print('✅ Users table with AI chat tracking columns created successfully')
        except Exception as error:
            print(f'❌ Error creating users table: {error}')
            raise error

    @staticmethod
    def register(user_data):
        """Register new user"""
        email = user_data.get('email')
        password = user_data.get('password')
        first_name = user_data.get('firstName')
        last_name = user_data.get('lastName')
        city = user_data.get('city')

        try:
            # Check if user already exists
            existing_user = User.find_by_email(email)
            if existing_user:
                raise ValueError('User with this email already exists')

            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insert new user (explicitly setting is_active = true)
            query = """
            INSERT INTO users (firstname, lastname, email, password_hash, city, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, firstname, lastname, email, city, created_at, is_active
            """

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (first_name, last_name, email, password_hash, city, True))
                    result = cursor.fetchone()
                    conn.commit()

            return User({
                'id': result['id'],
                'email': result['email'],
                'firstname': result['firstname'],
                'lastname': result['lastname'],
                'city': result['city'],
                'created_at': result['created_at'],
                'is_active': result['is_active']
            })

        except Exception as error:
            print(f'❌ Error registering user: {error}')
            raise error

    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        try:
            query = 'SELECT * FROM users WHERE email = %s AND is_active = true'
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (email,))
                    result = cursor.fetchone()

            if not result:
                return None

            return User({
                'id': result['id'],
                'email': result['email'],
                'firstname': result['firstname'],
                'lastname': result['lastname'],
                'city': result['city'],
                'created_at': result['created_at'],
                'last_login': result['last_login'],
                'is_active': result['is_active']
            })

        except Exception as error:
            print(f'❌ Error finding user by email: {error}')
            raise error

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        try:
            query = 'SELECT * FROM users WHERE id = %s AND is_active = true'
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (user_id,))
                    result = cursor.fetchone()

            if not result:
                return None

            return User({
                'id': result['id'],
                'email': result['email'],
                'firstname': result['firstname'],
                'lastname': result['lastname'],
                'city': result['city'],
                'created_at': result['created_at'],
                'last_login': result['last_login'],
                'is_active': result['is_active']
            })

        except Exception as error:
            print(f'❌ Error finding user by ID: {error}')
            raise error

    @staticmethod
    def authenticate(email, password):
        """Authenticate user"""
        try:
            query = 'SELECT * FROM users WHERE email = %s AND is_active = true'
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (email,))
                    result = cursor.fetchone()

            if not result:
                return None

            # Check password
            if not bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8')):
                return None

            # Update last login
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s', (result['id'],))
                    conn.commit()

            return User({
                'id': result['id'],
                'email': result['email'],
                'firstname': result['firstname'],
                'lastname': result['lastname'],
                'city': result['city'],
                'created_at': result['created_at'],
                'last_login': datetime.now(),
                'is_active': result['is_active']
            })

        except Exception as error:
            print(f'❌ Error authenticating user: {error}')
            raise error

    def verify_password(self, password):
        """Verify user's password"""
        try:
            query = 'SELECT password_hash FROM users WHERE id = %s AND is_active = true'
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (self.id,))
                    result = cursor.fetchone()

            if not result:
                return False

            # Check password
            return bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8'))

        except Exception as error:
            print(f'❌ Error verifying password: {error}')
            return False

    def change_password(self, new_password):
        """Change user's password"""
        try:
            # Hash the new password
            new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            query = 'UPDATE users SET password_hash = %s WHERE id = %s AND is_active = true'
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (new_password_hash, self.id))
                    conn.commit()
                    
                    # Check if the update was successful
                    if cursor.rowcount > 0:
                        return True
                    else:
                        return False

        except Exception as error:
            print(f'❌ Error changing password: {error}')
            return False

    def update_profile(self, update_data):
        """Update user profile - only updates provided fields"""
        try:
            # Map frontend field names to database column names
            field_mapping = {
                'firstName': 'firstname',
                'lastName': 'lastname', 
                'city': 'city'
            }
            
            # Build dynamic update query
            update_fields = []
            values = []
            
            for frontend_field, db_column in field_mapping.items():
                if frontend_field in update_data and update_data[frontend_field] is not None:
                    update_fields.append(f"{db_column} = %s")
                    values.append(update_data[frontend_field])
            
            if not update_fields:
                # No fields to update
                return self
            
            # Add user ID to values
            values.append(self.id)
            
            query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
            """

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    result = cursor.fetchone()
                    conn.commit()

            if result:
                # Update object properties
                self.first_name = result['firstname']
                self.last_name = result['lastname']
                self.city = result['city']

            return self

        except Exception as error:
            print(f'❌ Error updating user profile: {error}')
            raise error

    def update_city(self, city):
        """Update user's city"""
        try:
            query = 'UPDATE users SET city = %s WHERE id = %s'
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (city, self.id))
                    conn.commit()
            
            self.city = city
            return True
            
        except Exception as error:
            print(f'❌ Error updating user city: {error}')
            raise error

    @staticmethod
    def check_ai_chat_limit(user_id, daily_limit):
        """Check if user has exceeded daily AI chat limit"""
        try:
            query = """
            SELECT ai_chat_count, ai_chat_date 
            FROM users 
            WHERE id = %s
            """
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (user_id,))
                    result = cursor.fetchone()
            
            if not result:
                return False  # User not found
            
            current_count, chat_date = result
            today = datetime.now().date()
            
            # If no previous chat date or it's a new day, allow chat
            if not chat_date or chat_date != today:
                return True
            
            # Check if under limit for today
            return current_count < daily_limit
            
        except Exception as error:
            print(f'❌ Error checking AI chat limit: {error}')
            return False  # Err on the side of caution

    @staticmethod
    def increment_ai_chat_usage(user_id):
        """Increment user's daily AI chat usage count - ONLY counts user inputs, not AI responses"""
        try:
            today = datetime.now().date()
            print(f"🔢 INCREMENTING AI chat usage for user {user_id} on {today}")
            print(f"🔢 This increment represents ONE USER INPUT MESSAGE (AI responses don't count)")
            
            query = """
            UPDATE users 
            SET ai_chat_count = CASE 
                WHEN ai_chat_date = %s THEN ai_chat_count + 1
                ELSE 1
            END,
            ai_chat_date = %s
            WHERE id = %s
            RETURNING ai_chat_count
            """
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (today, today, user_id))
                    result = cursor.fetchone()
                    conn.commit()
            
            new_count = result[0] if result else 1
            print(f"🔢 User {user_id} now has {new_count} INPUT messages today (AI responses not counted)")
            return new_count
            
        except Exception as error:
            print(f'❌ Error incrementing AI chat usage: {error}')
            raise error

    @staticmethod
    def get_ai_chat_usage(user_id):
        """Get user's AI chat usage for today"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT ai_chat_count, ai_chat_date 
                        FROM users 
                        WHERE id = %s
                    """, (user_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        return {'current_usage': 0, 'date': None}
                    
                    current_count = result['ai_chat_count'] or 0
                    chat_date = result['ai_chat_date']
                    today = datetime.now().date()
                    
                    # If no previous chat date or it's a new day, return 0 usage
                    if not chat_date or chat_date != today:
                        return {'current_usage': 0, 'date': today.isoformat()}
                    
                    # Return actual usage for today
                    return {
                        'current_usage': current_count,
                        'date': chat_date.isoformat() if chat_date else None
                    }
                    
        except Exception as error:
            print(f'❌ Error getting AI chat usage: {error}')
            return {'current_usage': 0, 'date': None}

    @staticmethod
    def delete_user(user_id):
        """Permanently delete user account and all related data"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Start transaction
                    cursor.execute("BEGIN")
                    
                    try:
                        # Delete user's related data in order (foreign key constraints)
                        # Use correct table names and handle non-existent tables gracefully
                        
                        # Delete from analytics_events table (not analytics)
                        try:
                            cursor.execute("DELETE FROM analytics_events WHERE user_id = %s", (user_id,))
                            print(f"✅ Deleted analytics_events for user {user_id}")
                        except Exception as e:
                            print(f"⚠️ Could not delete from analytics_events: {e}")
                            # Continue with deletion even if this table doesn't exist
                        
                        # Delete from offer_analytics table
                        try:
                            cursor.execute("DELETE FROM offer_analytics WHERE user_id = %s", (user_id,))
                            print(f"✅ Deleted offer_analytics for user {user_id}")
                        except Exception as e:
                            print(f"⚠️ Could not delete from offer_analytics: {e}")
                            # Continue with deletion even if this table doesn't exist
                        
                        # Note: user_sessions table doesn't exist - Flask handles sessions in memory/cookies
                        # Removing this line as it causes the error
                        
                        # Finally delete the user - this is the most important part
                        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                        
                        # Check if user was actually deleted
                        if cursor.rowcount == 0:
                            raise Exception("User not found or already deleted")
                        
                        # Commit transaction
                        cursor.execute("COMMIT")
                        print(f"✅ User {user_id} and all related data deleted successfully")
                        return True
                        
                    except Exception as e:
                        # Rollback on any error
                        cursor.execute("ROLLBACK")
                        raise e
                        
        except Exception as e:
            print(f"❌ Error deleting user {user_id}: {e}")
            raise Exception(f"Failed to delete user: {str(e)}")

    @staticmethod
    def create_password_reset_token(email):
        """Generate a temporary password for the user and update their password"""
        try:
            import secrets
            import string
            
            # Check if user exists
            user = User.find_by_email(email)
            if not user:
                return None
            
            # Generate temporary password (8 characters, mix of letters and numbers)
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            
            # Hash the temporary password
            password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update user's password with temporary password
            query = "UPDATE users SET password_hash = %s WHERE email = %s"
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (password_hash, email))
                    conn.commit()
            
            return temp_password
            
        except Exception as error:
            print(f'❌ Error creating temporary password: {error}')
            raise error

    @staticmethod
    def verify_reset_token(email, token):
        """Not needed for temporary password approach"""
        return True

    @staticmethod
    def reset_password_with_token(email, token, new_password):
        """Not needed for temporary password approach - user will login with temp password and change it normally"""
        return True

    @staticmethod
    def update_database_schema():
        """No database schema changes needed for temporary password approach"""
        print('✅ No database schema changes needed for temporary password approach')

    @staticmethod
    def update_database_schema():
        """Update database schema to include password reset fields"""
        try:
            query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255),
            ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;
            """
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            
            print('✅ Database schema updated for password reset functionality')
            
        except Exception as error:
            print(f'❌ Error updating database schema: {error}')
            raise error 