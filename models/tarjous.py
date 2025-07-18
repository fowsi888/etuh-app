import uuid
from datetime import datetime
from config.database import get_db_connection
import psycopg2.extras

class Tarjous:
    def __init__(self, tarjous_data):
        self.id = tarjous_data.get('id')
        self.title = tarjous_data.get('title')
        self.description = tarjous_data.get('description')
        self.keywords = tarjous_data.get('keywords')
        self.category = tarjous_data.get('category')
        self.offer_type = tarjous_data.get('offer_type')
        self.status = tarjous_data.get('status', 'approved')
        self.is_premium = tarjous_data.get('is_premium', False)
        self.cost = tarjous_data.get('cost')
        self.created_at = tarjous_data.get('created_at')
        self.expires_at = tarjous_data.get('expires_at')
        self.approved_at = tarjous_data.get('approved_at')
        self.address = tarjous_data.get('address')
        self.city = tarjous_data.get('city')
        self.image_url = tarjous_data.get('image_url')
        self.starts_at = tarjous_data.get('starts_at')
        self.image_s3_key = tarjous_data.get('image_s3_key')
        self.is_nationwide = tarjous_data.get('is_nationwide', False)
        self.location_type = tarjous_data.get('location_type')
        self.offer_url = tarjous_data.get('offer_url')
        self.business_id = tarjous_data.get('business_id')
        
        # Business information from JOIN
        self.business_name = tarjous_data.get('business_name')
        self.phone = tarjous_data.get('phone')
        self.email = tarjous_data.get('email')

    def get_additional_images(self):
        """Get additional images from offer_images table (excluding primary image)"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT image_url, image_s3_key, "order"
                        FROM offer_images 
                        WHERE offer_id = %s 
                        ORDER BY "order" ASC, created_at ASC
                    """, (self.id,))
                    offer_images = cursor.fetchall()
            
            # Return list of image URLs, excluding the primary image to avoid duplication
            additional_images = []
            for img in offer_images:
                if img['image_url'] and img['image_url'] != self.image_url:
                    additional_images.append(img['image_url'])
            
            return additional_images
            
        except Exception as error:
            print(f'❌ Error getting additional images for offer {self.id}: {error}')
            return []

    def to_dict(self):
        """Convert tarjous object to dictionary"""
        # Get additional images from offer_images table
        additional_images = self.get_additional_images()
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'keywords': self.keywords,
            'imageUrl': self.image_url,
            'additionalImages': additional_images,
            'categoryName': self.category,
            'category': self.category,
            'offerType': self.offer_type,
            'merchantName': self.business_name,
            'businessName': self.business_name,
            'merchantAddress': self.address,
            'businessAddress': self.address,
            'address': self.address,
            'merchantPhone': self.phone,
            'businessPhone': self.phone,
            'phone': self.phone,
            'merchantWebsite': self.offer_url,
            'businessWebsite': self.offer_url,
            'website': self.offer_url,
            'offerUrl': self.offer_url,
            'email': self.email,
            'validFrom': self.starts_at.isoformat() if self.starts_at else None,
            'validUntil': self.expires_at.isoformat() if self.expires_at else None,
            'startsAt': self.starts_at.isoformat() if self.starts_at else None,
            'expiresAt': self.expires_at.isoformat() if self.expires_at else None,
            'isActive': self.status == 'approved',
            'status': self.status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'approvedAt': self.approved_at.isoformat() if self.approved_at else None,
            'city': self.city,
            'businessId': self.business_id,
            'isPremium': self.is_premium,
            'isNationwide': self.is_nationwide,
            'locationType': self.location_type,
            'cost': float(self.cost) if self.cost else None,
            'imageS3Key': self.image_s3_key
        }

    @staticmethod
    def create_table():
        """Create tarjoukset table if not exists"""
        query = """
        CREATE TABLE IF NOT EXISTS tarjoukset (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(255) NOT NULL,
            description TEXT,
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
        
        CREATE INDEX IF NOT EXISTS idx_tarjoukset_active ON tarjoukset(is_active);
        CREATE INDEX IF NOT EXISTS idx_tarjoukset_category ON tarjoukset(category_name);
        CREATE INDEX IF NOT EXISTS idx_tarjoukset_merchant ON tarjoukset(merchant_name);
        CREATE INDEX IF NOT EXISTS idx_tarjoukset_valid_until ON tarjoukset(valid_until);
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            print('✅ Tarjoukset table created successfully')
        except Exception as error:
            print(f'❌ Error creating tarjoukset table: {error}')
            raise error

    @staticmethod
    def get_offers(page=1, limit=20, category=None, city=None):
        """Get paginated offers from offers table with business information"""
        try:
            offset = (page - 1) * limit
            
            # Build WHERE clause for active offers - exclude hidden offers
            where_clause = "WHERE o.status = 'approved' AND (o.expires_at IS NULL OR o.expires_at > CURRENT_TIMESTAMP)"
            params = []
            
            if category:
                where_clause += " AND LOWER(o.category) = LOWER(%s)"
                params.append(category)
            
            if city:
                # Simple city filtering - handle JSON arrays and text
                where_clause += " AND (o.city::text ILIKE %s OR o.city::text ILIKE %s)"
                params.extend([f'%{city}%', '%koko maa%'])
            
            # Combined query using window function to get both data and count
            combined_query = f"""
            SELECT o.*, b.business_name, b.phone, b.email,
                   COUNT(*) OVER() as total_count
            FROM offers o 
            LEFT JOIN businesses b ON o.business_id = b.id
            {where_clause}
            ORDER BY o.is_premium DESC, o.created_at DESC 
            LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            # Debug logging
            print(f"🔍 SQL Query: {combined_query}")
            print(f"🔍 Parameters: {params}")
            print(f"🔍 Parameter count: {len(params)}")
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(combined_query, params)
                    results = cursor.fetchall()
            
            print(f"🔍 Query results count: {len(results)}")
            if results:
                print(f"🔍 First result keys: {list(results[0].keys())}")
            
            # Extract total count from first row (all rows have same total_count due to window function)
            total_count = results[0]['total_count'] if results and len(results) > 0 else 0
            
            # Convert to Tarjous objects, excluding the total_count field
            offers = []
            for row in results:
                row_dict = dict(row)
                # Remove total_count from the row data before creating Tarjous object
                row_dict.pop('total_count', None)
                offers.append(Tarjous(row_dict).to_dict())
            
            # Calculate pagination
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'offers': offers,
                'pagination': {
                    'currentPage': page,
                    'totalPages': total_pages,
                    'totalCount': total_count,
                    'hasNext': has_next,
                    'hasPrev': has_prev
                }
            }
            
        except Exception as error:
            print(f'❌ Error getting offers: {error}')
            import traceback
            print(f'❌ Full traceback: {traceback.format_exc()}')
            raise error

    @staticmethod
    def search_offers(search_term, page=1, limit=20):
        """Search offers by title, description, keywords, or business name with business information"""
        try:
            offset = (page - 1) * limit
            search_pattern = f"%{search_term}%"
            
            # Combined search query using window function to get both data and count - exclude hidden offers
            combined_search_query = """
            SELECT o.*, b.business_name, b.phone, b.email,
                   COUNT(*) OVER() as total_count
            FROM offers o 
            LEFT JOIN businesses b ON o.business_id = b.id 
            WHERE o.status = 'approved'
            AND (o.expires_at IS NULL OR o.expires_at > CURRENT_TIMESTAMP)
            AND (
                LOWER(o.title) LIKE LOWER(%s) OR 
                LOWER(o.description) LIKE LOWER(%s) OR 
                LOWER(o.keywords) LIKE LOWER(%s) OR
                LOWER(o.category) LIKE LOWER(%s) OR
                LOWER(b.business_name) LIKE LOWER(%s)
            )
            ORDER BY 
                CASE WHEN LOWER(o.title) LIKE LOWER(%s) THEN 1 ELSE 2 END,
                o.is_premium DESC,
                o.created_at DESC
            LIMIT %s OFFSET %s
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(combined_search_query, (
                        search_pattern, search_pattern, search_pattern, search_pattern, search_pattern,
                        search_pattern, limit, offset
                    ))
                    results = cursor.fetchall()
            
            # Extract total count from first row (all rows have same total_count due to window function)
            total_count = results[0]['total_count'] if results else 0
            
            # Convert to Tarjous objects, excluding the total_count field
            offers = []
            for row in results:
                row_dict = dict(row)
                # Remove total_count from the row data before creating Tarjous object
                row_dict.pop('total_count', None)
                offers.append(Tarjous(row_dict).to_dict())
            
            # Calculate pagination
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'offers': offers,
                'pagination': {
                    'currentPage': page,
                    'totalPages': total_pages,
                    'totalCount': total_count,
                    'hasNext': has_next,
                    'hasPrev': has_prev
                }
            }
            
        except Exception as error:
            print(f'❌ Error searching offers: {error}')
            raise error

    @staticmethod
    def find_by_id(offer_id):
        """Find offer by ID with business information"""
        try:
            query = """
            SELECT o.*, b.business_name, b.phone, b.email
            FROM offers o 
            LEFT JOIN businesses b ON o.business_id = b.id 
            WHERE o.id = %s AND o.status = 'approved'
            AND (o.expires_at IS NULL OR o.expires_at > CURRENT_TIMESTAMP)
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (offer_id,))
                    result = cursor.fetchone()
            
            if not result:
                return None
            
            return Tarjous(dict(result))
            
        except Exception as error:
            print(f'❌ Error finding offer by ID: {error}')
            raise error

    @staticmethod
    def create_offer(offer_data):
        """Create new offer"""
        try:
            query = """
            INSERT INTO tarjoukset (
                title, description, image_url, category_name, merchant_name, merchant_address, merchant_phone,
                merchant_website, valid_from, valid_until, terms
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING *
            """
            
            values = (
                offer_data.get('title'),
                offer_data.get('description'),
                offer_data.get('imageUrl'),
                offer_data.get('categoryName'),
                offer_data.get('merchantName'),
                offer_data.get('merchantAddress'),
                offer_data.get('merchantPhone'),
                offer_data.get('merchantWebsite'),
                offer_data.get('validFrom'),
                offer_data.get('validUntil'),
                offer_data.get('terms')
            )
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    result = cursor.fetchone()
                    conn.commit()
            
            return Tarjous(dict(result))
            
        except Exception as error:
            print(f'❌ Error creating offer: {error}')
            raise error

 