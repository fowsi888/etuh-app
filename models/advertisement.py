from datetime import datetime
from config.database import get_db_connection
import psycopg2.extras

class Advertisement:
    def __init__(self, ad_data):
        self.id = ad_data.get('id')
        self.title = ad_data.get('title')
        self.subtitle = ad_data.get('subtitle')
        self.icon = ad_data.get('icon')
        self.icon_type = ad_data.get('icon_type', 'emoji')
        self.icon_url = ad_data.get('icon_url')
        self.icon_s3_key = ad_data.get('icon_s3_key')
        self.background_gradient = ad_data.get('background_gradient')
        self.cta_text = ad_data.get('cta_text')
        self.cta_url = ad_data.get('cta_url')
        self.category = ad_data.get('category')
        self.is_active = ad_data.get('is_active', True)
        self.display_priority = ad_data.get('display_priority', 1)
        self.clicks = ad_data.get('clicks', 0)
        self.created_at = ad_data.get('created_at')
        self.expiration_date = ad_data.get('expiration_date')

    def to_dict(self):
        """Convert advertisement object to dictionary for API response"""
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'iconType': self.icon_type,
            'iconUrl': self.icon_url,
            'iconS3Key': self.icon_s3_key,
            'backgroundGradient': self.background_gradient,
            'background': self.background_gradient,  # Alias for compatibility
            'ctaText': self.cta_text,
            'cta': self.cta_text,  # Alias for compatibility
            'ctaUrl': self.cta_url,
            'category': self.category,
            'isActive': self.is_active,
            'displayPriority': self.display_priority,
            'clicks': self.clicks,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'expirationDate': self.expiration_date.isoformat() if self.expiration_date else None
        }

    @staticmethod
    def get_active_ads(limit=10):
        """Get active advertisements for display - only returns ads where is_active = true"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Updated query to include icon fields
                    cursor.execute("""
                        SELECT id, title, subtitle, icon, icon_type, icon_url, icon_s3_key,
                               background_gradient, cta_text, cta_url, category, 
                               display_priority, clicks, created_at, expiration_date
                        FROM advertisements 
                        WHERE is_active = true
                        AND (expiration_date IS NULL OR expiration_date > CURRENT_DATE)
                        ORDER BY display_priority DESC, RANDOM()
                        LIMIT %s
                    """, (limit,))
                    results = cursor.fetchall()
            
            # Convert to Advertisement objects and return as dictionaries
            ads = [Advertisement(dict(row)).to_dict() for row in results]
            return ads
            
        except Exception as error:
            print(f'❌ Error getting active advertisements: {error}')
            return []

    @staticmethod
    def track_click(ad_id):
        """Track a click for an advertisement - only for active ads"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Only track clicks for active advertisements
                    cursor.execute("""
                        UPDATE advertisements 
                        SET clicks = clicks + 1
                        WHERE id = %s AND is_active = true
                        RETURNING id
                    """, (ad_id,))
                    result = cursor.fetchone()
                    conn.commit()
            
            # Return True only if a row was actually updated (ad exists and is active)
            return result is not None
            
        except Exception as error:
            print(f'❌ Error tracking click for ad {ad_id}: {error}')
            return False

    @staticmethod
    def find_by_id(ad_id):
        """Find advertisement by ID"""
        try:
            query = "SELECT * FROM advertisements WHERE id = %s"
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (ad_id,))
                    result = cursor.fetchone()
            
            if not result:
                return None
            
            return Advertisement(dict(result))
            
        except Exception as error:
            print(f'❌ Error finding advertisement by ID: {error}')
            raise error

    @staticmethod
    def get_stats():
        """Get simple advertisement statistics"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_ads,
                            COUNT(*) FILTER (WHERE is_active = true) as active_ads,
                            SUM(clicks) as total_clicks
                        FROM advertisements
                    """)
                    stats = cursor.fetchone()
                    
                    return {
                        'totalAds': stats[0] or 0,
                        'activeAds': stats[1] or 0,
                        'totalClicks': stats[2] or 0
                    }
            
        except Exception as error:
            print(f'❌ Error getting advertisement stats: {error}')
            return {
                'totalAds': 0,
                'activeAds': 0,
                'totalClicks': 0
            } 