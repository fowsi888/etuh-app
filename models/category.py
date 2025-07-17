import uuid
from datetime import datetime
from config.database import get_db_connection
import psycopg2.extras

class Category:
    def __init__(self, category_data):
        self.id = category_data.get('id')
        self.name = category_data.get('name')
        # For compatibility with frontend, use name as both fi and en
        self.name_fi = category_data.get('name_fi') or category_data.get('name')
        self.name_en = category_data.get('name_en') or category_data.get('name')
        self.description = category_data.get('description')
        self.icon = category_data.get('icon')
        self.is_active = category_data.get('is_active', True)
        self.created_at = category_data.get('created_at')
        self.updated_at = category_data.get('updated_at')

    def to_dict(self):
        return {
            'id': str(self.id) if self.id else None,
            'name': self.name,
            'name_fi': self.name_fi,
            'name_en': self.name_en,
            'description': self.description,
            'icon': self.icon,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def create_table():
        """Create categories table if not exists"""
        query = """
        CREATE TABLE IF NOT EXISTS categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            name_fi VARCHAR(100) NOT NULL,
            name_en VARCHAR(100) NOT NULL,
            description TEXT,
            icon VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_categories_active ON categories(is_active);
        CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            print('✅ Categories table created successfully')
        except Exception as error:
            print(f'❌ Error creating categories table: {error}')
            raise error

    @staticmethod
    def get_all_categories():
        """Get all categories from the existing simple table structure"""
        try:
            query = "SELECT * FROM categories ORDER BY name"
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
            
            categories = []
            for row in results:
                category_data = {
                    'id': row['id'],
                    'name': row['name'],
                    'name_fi': row['name'],  # Use name as Finnish name
                    'name_en': row['name'],  # Use name as English name
                    'is_active': True  # Assume all categories are active
                }
                categories.append(Category(category_data).to_dict())
            
            return categories
            
        except Exception as error:
            print(f'❌ Error getting categories: {error}')
            raise error

    @staticmethod
    def get_category_by_id(category_id):
        """Get category by ID"""
        try:
            query = "SELECT * FROM categories WHERE id = %s"
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (category_id,))
                    result = cursor.fetchone()
            
            if result:
                category_data = {
                    'id': result['id'],
                    'name': result['name'],
                    'name_fi': result['name'],
                    'name_en': result['name'],
                    'is_active': True
                }
                return Category(category_data).to_dict()
            return None
            
        except Exception as error:
            print(f'❌ Error getting category by ID: {error}')
            raise error

    @staticmethod
    def create_category(category_data):
        """Create new category"""
        try:
            query = """
            INSERT INTO categories (name, name_fi, name_en, description, icon)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """
            
            values = (
                category_data.get('name'),
                category_data.get('name_fi'),
                category_data.get('name_en'),
                category_data.get('description'),
                category_data.get('icon')
            )
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    result = cursor.fetchone()
                    conn.commit()
            
            return Category(dict(result)).to_dict()
            
        except Exception as error:
            print(f'❌ Error creating category: {error}')
            raise error

    @staticmethod
    def add_default_categories():
        """Add default categories to the database"""
        default_categories = [
            {
                'name': 'food',
                'name_fi': 'Ruoka',
                'name_en': 'Food',
                'description': 'Food and dining offers',
                'icon': '🍽️'
            },
            {
                'name': 'fashion',
                'name_fi': 'Muoti',
                'name_en': 'Fashion',
                'description': 'Fashion and clothing offers',
                'icon': '👗'
            },
            {
                'name': 'electronics',
                'name_fi': 'Elektroniikka',
                'name_en': 'Electronics',
                'description': 'Electronics and technology offers',
                'icon': '📱'
            },
            {
                'name': 'health',
                'name_fi': 'Terveys',
                'name_en': 'Health',
                'description': 'Health and wellness offers',
                'icon': '🏥'
            },
            {
                'name': 'beauty',
                'name_fi': 'Kauneus',
                'name_en': 'Beauty',
                'description': 'Beauty and cosmetics offers',
                'icon': '💄'
            },
            {
                'name': 'sports',
                'name_fi': 'Urheilu',
                'name_en': 'Sports',
                'description': 'Sports and fitness offers',
                'icon': '⚽'
            },
            {
                'name': 'home',
                'name_fi': 'Koti',
                'name_en': 'Home',
                'description': 'Home and garden offers',
                'icon': '🏠'
            },
            {
                'name': 'travel',
                'name_fi': 'Matkailu',
                'name_en': 'Travel',
                'description': 'Travel and tourism offers',
                'icon': '✈️'
            },
            {
                'name': 'entertainment',
                'name_fi': 'Viihde',
                'name_en': 'Entertainment',
                'description': 'Entertainment and leisure offers',
                'icon': '🎬'
            },
            {
                'name': 'automotive',
                'name_fi': 'Autot',
                'name_en': 'Automotive',
                'description': 'Automotive and transportation offers',
                'icon': '🚗'
            }
        ]
        
        try:
            for category_data in default_categories:
                # Check if category already exists
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM categories WHERE name = %s", (category_data['name'],))
                        if cursor.fetchone()[0] == 0:
                            Category.create_category(category_data)
            
            print('✅ Default categories added successfully')
        except Exception as error:
            print(f'❌ Error adding default categories: {error}')
            raise error 