#!/usr/bin/env python3

import psycopg2
import psycopg2.extras
from datetime import date
from config.database import get_db_connection

class OfferAnalytics:
    """Handle analytics data specifically for the offer_analytics table"""
    
    @staticmethod
    def track_offer_interaction(offer_id, user_id=None, event_type='view'):
        """Track user interactions with offers and include user city information"""
        try:
            today = date.today()
            user_city = None
            
            # Get user city if user_id is provided
            if user_id:
                user_city = OfferAnalytics._get_user_city(user_id)
            
            print(f"📊 Tracking {event_type} for offer {offer_id}, user {user_id}, city: {user_city}")
            
            # Check if this user has already been tracked for this offer today
            if user_id and OfferAnalytics._is_user_already_tracked_today(offer_id, user_id, today):
                print(f"⚠️ User {user_id} already tracked for offer {offer_id} today - skipping")
                return True  # Return True but don't increment counters
            
            # Check if record exists for this offer and date
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id FROM offer_analytics 
                        WHERE offer_id = %s AND date = %s
                    """, (offer_id, today))
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Create new record with default values
                        cursor.execute("""
                            INSERT INTO offer_analytics 
                            (offer_id, date, views, clicks, conversions, 
                             conversion_calls, conversion_directions, conversion_website,
                             user_id, user_city, created_at) 
                            VALUES (%s, %s, 0, 0, 0, 0, 0, 0, %s, %s, CURRENT_TIMESTAMP)
                        """, (offer_id, today, user_id, user_city))
                        conn.commit()
                        print(f"📝 Created new offer_analytics record for offer {offer_id} on {today}")
            
            # Update the appropriate counter based on event type
            field_mapping = {
                'view': 'views',
                'click': 'clicks',
                'conversion': 'conversions'
            }
            
            field = field_mapping.get(event_type)
            if not field:
                print(f"⚠️ Unknown event type for offer analytics: {event_type}")
                return False
            
            # Update the counter and user information
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE offer_analytics 
                        SET {field} = {field} + 1,
                            user_id = COALESCE(user_id, %s),
                            user_city = COALESCE(user_city, %s)
                        WHERE offer_id = %s AND date = %s
                    """, (user_id, user_city, offer_id, today))
                    conn.commit()
            
            print(f"✅ Updated {event_type} for offer {offer_id} on {today} with city {user_city}")
            return True
                    
        except Exception as error:
            print(f'❌ Error tracking offer interaction: {error}')
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def track_conversion(offer_id, conversion_type, user_id=None):
        """Track specific conversion types with user city information"""
        try:
            today = date.today()
            user_city = None
            
            # Get user city if user_id is provided
            if user_id:
                user_city = OfferAnalytics._get_user_city(user_id)
            
            print(f"📊 Tracking {conversion_type} conversion for offer {offer_id}, user {user_id}, city: {user_city}")
            
            # Check if this user has already performed this specific conversion type today
            if user_id and OfferAnalytics._has_user_converted_today(offer_id, user_id, conversion_type, today):
                print(f"⚠️ User {user_id} already performed {conversion_type} conversion for offer {offer_id} today - skipping")
                return True  # Return True but don't increment counters
            
            # Check if record exists for this offer and date
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id FROM offer_analytics 
                        WHERE offer_id = %s AND date = %s
                    """, (offer_id, today))
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Create new record with default values
                        cursor.execute("""
                            INSERT INTO offer_analytics 
                            (offer_id, date, views, clicks, conversions, 
                             conversion_calls, conversion_directions, conversion_website,
                             user_id, user_city, created_at) 
                            VALUES (%s, %s, 0, 0, 0, 0, 0, 0, %s, %s, CURRENT_TIMESTAMP)
                        """, (offer_id, today, user_id, user_city))
                        conn.commit()
                        print(f"📝 Created new offer_analytics record for offer {offer_id} on {today}")
            
            # Map conversion types to database fields
            conversion_field_mapping = {
                'website': 'conversion_website',
                'call': 'conversion_calls',
                'directions': 'conversion_directions'
            }
            
            field = conversion_field_mapping.get(conversion_type)
            if not field:
                print(f"⚠️ Unknown conversion type for offer analytics: {conversion_type}")
                return False
            
            # Update the specific conversion counter, total conversions, and user information
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE offer_analytics 
                        SET {field} = {field} + 1,
                            conversions = conversions + 1,
                            user_id = COALESCE(user_id, %s),
                            user_city = COALESCE(user_city, %s)
                        WHERE offer_id = %s AND date = %s
                    """, (user_id, user_city, offer_id, today))
                    conn.commit()
            
            print(f"✅ Tracked {conversion_type} conversion for offer {offer_id} on {today} with city {user_city}")
            return True
                    
        except Exception as error:
            print(f'❌ Error tracking conversion: {error}')
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _is_user_already_tracked_today(offer_id, user_id, event_date):
        """Check if user has already been tracked for this offer today by looking at existing records"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Check if there's already a record with this user_id for this offer and date
                    cursor.execute("""
                        SELECT id FROM offer_analytics 
                        WHERE offer_id = %s AND user_id = %s AND date = %s
                    """, (offer_id, user_id, event_date))
                    existing_record = cursor.fetchone()
                    
                    return existing_record is not None
                    
        except Exception as error:
            print(f'❌ Error checking if user already tracked: {error}')
            return False  # If there's an error, allow tracking to prevent blocking

    @staticmethod
    def _get_user_city(user_id):
        """Get user's city from the users table"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("SELECT city FROM users WHERE id = %s", (user_id,))
                    result = cursor.fetchone()
                    
                    if result and result['city']:
                        return result['city']
                    else:
                        return None  # City not set for this user
                        
        except Exception as error:
            print(f'❌ Error getting user city: {error}')
            return None

    @staticmethod
    def get_city_analytics(start_date=None, end_date=None):
        """Get analytics data grouped by city for analysis"""
        try:
            date_filter = ""
            params = []
            
            if start_date and end_date:
                date_filter = "WHERE date BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            query = f"""
            SELECT 
                COALESCE(user_city, 'Unknown') as city,
                SUM(views) as total_views,
                SUM(clicks) as total_clicks,
                SUM(conversions) as total_conversions,
                SUM(conversion_calls) as total_calls,
                SUM(conversion_directions) as total_directions,
                SUM(conversion_website) as total_website,
                COUNT(DISTINCT offer_id) as unique_offers,
                ROUND(
                    SUM(conversions)::numeric / 
                    NULLIF(SUM(views), 0) * 100, 2
                ) as conversion_rate
            FROM offer_analytics 
            {date_filter}
            GROUP BY user_city
            ORDER BY total_views DESC
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as error:
            print(f'❌ Error getting city analytics: {error}')
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_offer_city_breakdown(offer_id, start_date=None, end_date=None):
        """Get city breakdown for a specific offer"""
        try:
            date_filter = ""
            params = [offer_id]
            
            if start_date and end_date:
                date_filter = "AND date BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            query = f"""
            SELECT 
                COALESCE(user_city, 'Unknown') as city,
                SUM(views) as views,
                SUM(clicks) as clicks,
                SUM(conversions) as conversions,
                SUM(conversion_calls) as calls,
                SUM(conversion_directions) as directions,
                SUM(conversion_website) as website,
                ROUND(
                    SUM(conversions)::numeric / 
                    NULLIF(SUM(views), 0) * 100, 2
                ) as conversion_rate
            FROM offer_analytics 
            WHERE offer_id = %s {date_filter}
            GROUP BY user_city
            ORDER BY views DESC
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as error:
            print(f'❌ Error getting offer city breakdown: {error}')
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _has_user_converted_today(offer_id, user_id, conversion_type, event_date):
        """Check if user has already performed this specific conversion type today using existing data"""
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Check existing offer_analytics records to see if user has already converted today
                    # We'll look for records where this user_id appears with the same offer_id and date
                    # and has already performed this specific conversion type
                    
                    conversion_field_mapping = {
                        'website': 'conversion_website',
                        'call': 'conversion_calls', 
                        'directions': 'conversion_directions'
                    }
                    
                    field = conversion_field_mapping.get(conversion_type)
                    if not field:
                        return False
                    
                    # Check if there's already a record for this user-offer-date with this conversion type > 0
                    cursor.execute(f"""
                        SELECT id FROM offer_analytics 
                        WHERE offer_id = %s AND user_id = %s AND date = %s AND {field} > 0
                    """, (offer_id, user_id, event_date))
                    existing_record = cursor.fetchone()
                    
                    return existing_record is not None
                    
        except Exception as error:
            print(f'❌ Error checking user conversion: {error}')
            return False  # If there's an error, allow tracking to prevent blocking 