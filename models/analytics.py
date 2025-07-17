import uuid
from datetime import datetime, date
from config.database import get_db_connection
import psycopg2.extras
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

class Analytics:
    # Thread pool executor for async operations
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analytics")
    
    @staticmethod
    def create_tables():
        """Create analytics tables if they don't exist"""
        query = """
        DROP TABLE IF EXISTS analytics_events CASCADE;
        DROP TABLE IF EXISTS analytics_daily_stats CASCADE;
        
        CREATE TABLE analytics_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(50) NOT NULL,
            session_id VARCHAR(255),
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            offer_id INTEGER REFERENCES offers(id) ON DELETE SET NULL,
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
        
        CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON analytics_events(user_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_events_offer ON analytics_events(offer_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_analytics_daily_stats_date ON analytics_daily_stats(date);
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    conn.commit()
            print('✅ Analytics tables created successfully')
        except Exception as error:
            print(f'❌ Error creating analytics tables: {error}')
            raise error

    @staticmethod
    def batch_track_events(events_data):
        """Batch track multiple analytics events in a single query"""
        try:
            if not events_data:
                return
                
            event_date = date.today()
            
            # Prepare data for batch insert
            analytics_values = []
            business_updates = {}  # Track business analytics updates
            
            for event in events_data:
                event_type = event.get('event_type')
                session_id = event.get('session_id')
                user_id = event.get('user_id')
                offer_id = event.get('offer_id')
                metadata = event.get('metadata')
                ip_address = event.get('ip_address')
                user_agent = event.get('user_agent')
                
                # Add to batch insert data
                analytics_values.append((
                    event_type, session_id, user_id, offer_id, 
                    json.dumps(metadata) if metadata else None, 
                    ip_address, user_agent
                ))
                
                # Track business analytics updates
                if offer_id and event_type in ['view', 'click', 'conversion']:
                    if offer_id not in business_updates:
                        business_updates[offer_id] = {'view': 0, 'click': 0, 'conversion': 0}
                    business_updates[offer_id][event_type] += 1
            
            # Single batch insert for analytics_events using execute_values
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    psycopg2.extras.execute_values(
                        cursor,
                        """INSERT INTO analytics_events (event_type, session_id, user_id, offer_id, metadata, ip_address, user_agent, created_at)
                           VALUES %s""",
                        [(event_type, session_id, user_id, offer_id, metadata, ip_address, user_agent, datetime.now()) 
                         for event_type, session_id, user_id, offer_id, metadata, ip_address, user_agent in analytics_values],
                        template=None,
                        page_size=100
                    )
                    conn.commit()
            
            # Batch update business analytics
            Analytics._batch_update_business_analytics(business_updates, event_date)
                
        except Exception as error:
            print(f'❌ Error in batch_track_events: {error}')
            # Don't raise the error to avoid breaking the main application flow
            pass

    @staticmethod
    def batch_track_events_async(events_data):
        """Async wrapper for batch_track_events - fire and forget"""
        try:
            Analytics._executor.submit(Analytics.batch_track_events, events_data)
        except Exception as error:
            print(f'❌ Error submitting async batch_track_events: {error}')
            pass

    @staticmethod
    def _batch_update_business_analytics(business_updates, event_date):
        """Batch update business analytics for multiple offers"""
        try:
            if not business_updates:
                return
                
            # Get business_ids for all offers in one query
            offer_ids = list(business_updates.keys())
            business_mapping = {}
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, business_id FROM offers WHERE id = ANY(%s)
                    """, (offer_ids,))
                    results = cursor.fetchall()
                    
                    for row in results:
                        business_mapping[row['id']] = row['business_id']
            
            # Group updates by business_id
            business_stats = {}
            for offer_id, stats in business_updates.items():
                business_id = business_mapping.get(offer_id)
                if business_id:
                    if business_id not in business_stats:
                        business_stats[business_id] = {'view': 0, 'click': 0, 'conversion': 0}
                    business_stats[business_id]['view'] += stats['view']
                    business_stats[business_id]['click'] += stats['click']
                    business_stats[business_id]['conversion'] += stats['conversion']
            
            # Handle each business separately - check if exists, then insert or update
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for business_id, stats in business_stats.items():
                        if stats['view'] > 0 or stats['click'] > 0 or stats['conversion'] > 0:
                            # Check if record exists
                            cursor.execute("""
                                SELECT id FROM business_analytics 
                                WHERE business_id = %s AND date = %s
                            """, (business_id, event_date))
                            existing_record = cursor.fetchone()
                            
                            if existing_record:
                                # Update existing record
                                cursor.execute("""
                                    UPDATE business_analytics 
                                    SET total_views = total_views + %s,
                                        total_clicks = total_clicks + %s,
                                        total_conversions = total_conversions + %s
                                    WHERE business_id = %s AND date = %s
                                """, (stats['view'], stats['click'], stats['conversion'], business_id, event_date))
                            else:
                                # Insert new record
                                cursor.execute("""
                                    INSERT INTO business_analytics (business_id, date, total_views, total_clicks, total_conversions, total_spent, active_offers, created_at)
                                    VALUES (%s, %s, %s, %s, %s, 0, 0, CURRENT_TIMESTAMP)
                                """, (business_id, event_date, stats['view'], stats['click'], stats['conversion']))
                    
                    conn.commit()
                    
        except Exception as error:
            print(f'❌ Error in _batch_update_business_analytics: {error}')
            pass

    @staticmethod
    def track_event(event_type, session_id, user_id=None, offer_id=None, metadata=None, ip_address=None, user_agent=None):
        """Track analytics events"""
        try:
            event_date = date.today()
            
            # Insert into analytics_events table
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO analytics_events (event_type, session_id, user_id, offer_id, metadata, ip_address, user_agent, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (event_type, session_id, user_id, offer_id, json.dumps(metadata) if metadata else None, ip_address, user_agent))
                    conn.commit()
            
            # Push to business analytics if offer_id is provided
            if offer_id:
                Analytics._push_to_business_analytics(event_type, offer_id, event_date)
                
        except Exception as error:
            # Don't raise the error to avoid breaking the main application flow
            pass

    @staticmethod
    def _push_to_business_analytics(event_type, offer_id, event_date):
        """Push analytics data to business_analytics table for business dashboard"""
        try:
            # First, get the business_id for this offer
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("SELECT business_id FROM offers WHERE id = %s", (offer_id,))
                    offer_result = cursor.fetchone()
                    
                    if not offer_result:
                        return
                    
                    business_id = offer_result['business_id']
            
            # Check if record exists for this business and date
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id FROM business_analytics 
                        WHERE business_id = %s AND date = %s
                    """, (business_id, event_date))
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Create new record
                        cursor.execute("""
                            INSERT INTO business_analytics (business_id, date, total_views, total_clicks, total_conversions, total_spent, active_offers, created_at) 
                            VALUES (%s, %s, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP)
                        """, (business_id, event_date))
                        conn.commit()
            
            # Update the appropriate counter based on event type
            field_mapping = {
                'view': 'total_views',
                'click': 'total_clicks', 
                'conversion': 'total_conversions'
            }
            
            field = field_mapping.get(event_type)
            if not field:
                return
            
            # Update the business analytics counter
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE business_analytics 
                        SET {field} = {field} + 1
                        WHERE business_id = %s AND date = %s
                    """, (business_id, event_date))
                    
                    # Also update active_offers count for this business
                    cursor.execute("""
                        UPDATE business_analytics 
                        SET active_offers = (
                            SELECT COUNT(*) 
                            FROM offers 
                            WHERE business_id = %s 
                            AND status = 'approved' 
                            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                        )
                        WHERE business_id = %s AND date = %s
                    """, (business_id, business_id, event_date))
                    
                    conn.commit()
                    
        except Exception as error:
            # Don't raise the error to avoid breaking the main tracking function
            pass

    @staticmethod
    def track_business_conversion(conversion_type, offer_id, event_date=None):
        """Track specific conversion types in business_analytics table"""
        if event_date is None:
            event_date = date.today()
            
        try:
            # First, get the business_id for this offer
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("SELECT business_id FROM offers WHERE id = %s", (offer_id,))
                    offer_result = cursor.fetchone()
                    
                    if not offer_result:
                        return
                    
                    business_id = offer_result['business_id']
            
            # Check if record exists for this business and date, create if not
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id FROM business_analytics 
                        WHERE business_id = %s AND date = %s
                    """, (business_id, event_date))
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Create new record with default values
                        cursor.execute("""
                            INSERT INTO business_analytics 
                            (business_id, date, total_views, total_clicks, total_conversions, 
                             total_spent, active_offers, conversion_calls, conversion_directions, 
                             conversion_website, created_at) 
                            VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP)
                        """, (business_id, event_date))
                        conn.commit()
            
            # Map conversion types to database fields
            conversion_field_mapping = {
                'website': 'conversion_website',
                'call': 'conversion_calls',
                'directions': 'conversion_directions'
            }
            
            field = conversion_field_mapping.get(conversion_type)
            if not field:
                return
            
            # Update the specific conversion counter and total conversions
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE business_analytics 
                        SET {field} = {field} + 1,
                            total_conversions = total_conversions + 1
                        WHERE business_id = %s AND date = %s
                    """, (business_id, event_date))
                    
                    # Also update active_offers count for this business
                    cursor.execute("""
                        UPDATE business_analytics 
                        SET active_offers = (
                            SELECT COUNT(*) 
                            FROM offers 
                            WHERE business_id = %s 
                            AND status = 'approved' 
                            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                        )
                        WHERE business_id = %s AND date = %s
                    """, (business_id, business_id, event_date))
                    
                    conn.commit()
                    
        except Exception as error:
            pass

    @staticmethod
    def get_dashboard_data(start_date, end_date):
        """Get dashboard analytics data for date range"""
        try:
            # Get daily stats for the period
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            date,
                            total_views,
                            total_clicks,
                            total_conversions,
                            unique_users,
                            top_categories,
                            top_merchants
                        FROM analytics_daily_stats 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY date
                    """, (start_date, end_date))
                    daily_stats = [dict(row) for row in cursor.fetchall()]
            
            # Get event summary for the period
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            event_type,
                            COUNT(*) as count,
                            COUNT(DISTINCT session_id) as unique_sessions,
                            COUNT(DISTINCT user_id) as unique_users
                        FROM analytics_events 
                        WHERE DATE(created_at) BETWEEN %s AND %s 
                        GROUP BY event_type
                    """, (start_date, end_date))
                    event_summary = [dict(row) for row in cursor.fetchall()]
            
            # Get top offers by views/clicks
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            o.title,
                            o.category,
                            COUNT(*) as event_count,
                            ae.event_type
                        FROM analytics_events ae
                        JOIN offers o ON ae.offer_id = o.id
                        WHERE DATE(ae.created_at) BETWEEN %s AND %s 
                        AND ae.event_type IN ('view', 'click')
                        GROUP BY o.id, o.title, o.category, ae.event_type
                        ORDER BY event_count DESC
                        LIMIT 10
                    """, (start_date, end_date))
                    top_offers = [dict(row) for row in cursor.fetchall()]
            
            # Calculate totals
            total_views = sum(stat['total_views'] or 0 for stat in daily_stats)
            total_clicks = sum(stat['total_clicks'] or 0 for stat in daily_stats)
            total_conversions = sum(stat['total_conversions'] or 0 for stat in daily_stats)
            
            # Calculate conversion rate
            conversion_rate = (total_conversions / total_views * 100) if total_views > 0 else 0
            click_through_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
            
            return {
                'summary': {
                    'totalViews': total_views,
                    'totalClicks': total_clicks,
                    'totalConversions': total_conversions,
                    'conversionRate': round(conversion_rate, 2),
                    'clickThroughRate': round(click_through_rate, 2)
                },
                'dailyStats': daily_stats,
                'eventSummary': event_summary,
                'topOffers': top_offers,
                'dateRange': {
                    'startDate': start_date,
                    'endDate': end_date
                }
            }
            
        except Exception as error:
            print(f'❌ Error getting dashboard data: {error}')
            raise error

    @staticmethod
    def get_offer_analytics(offer_id, start_date=None, end_date=None):
        """Get analytics for a specific offer"""
        try:
            where_clause = "WHERE offer_id = %s"
            params = [offer_id]
            
            if start_date and end_date:
                where_clause += " AND DATE(created_at) BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(f"""
                        SELECT 
                            event_type,
                            COUNT(*) as count,
                            COUNT(DISTINCT session_id) as unique_sessions,
                            COUNT(DISTINCT user_id) as unique_users,
                            DATE(created_at) as event_date
                        FROM analytics_events 
                        {where_clause}
                        GROUP BY event_type, DATE(created_at)
                        ORDER BY event_date DESC, event_type
                    """, params)
                    results = [dict(row) for row in cursor.fetchall()]
            
            return results
            
        except Exception as error:
            print(f'❌ Error getting offer analytics: {error}')
            raise error

    @staticmethod
    def get_user_analytics(user_id, start_date=None, end_date=None):
        """Get analytics for a specific user"""
        try:
            where_clause = "WHERE user_id = %s"
            params = [user_id]
            
            if start_date and end_date:
                where_clause += " AND DATE(created_at) BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(f"""
                        SELECT 
                            ae.event_type,
                            ae.created_at,
                            o.title as offer_title,
                            o.category,
                            ae.metadata
                        FROM analytics_events ae
                        LEFT JOIN offers o ON ae.offer_id = o.id
                        {where_clause}
                        ORDER BY ae.created_at DESC
                        LIMIT 100
                    """, params)
                    results = [dict(row) for row in cursor.fetchall()]
            
            return results
            
        except Exception as error:
            print(f'❌ Error getting user analytics: {error}')
            raise error

    @staticmethod
    def get_location_analytics(start_date=None, end_date=None):
        """Get analytics data grouped by location for business dashboard"""
        try:
            date_filter = ""
            params = []
            
            if start_date and end_date:
                date_filter = "WHERE ae.created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            query = f"""
            SELECT 
                ae.metadata->>'userLocation'->>'lat' as latitude,
                ae.metadata->>'userLocation'->>'lng' as longitude,
                COALESCE(ae.metadata->>'city', 'Unknown') as city,
                COUNT(CASE WHEN ae.event_type = 'view' THEN 1 END) as total_views,
                COUNT(CASE WHEN ae.event_type = 'click' THEN 1 END) as total_clicks,
                COUNT(CASE WHEN ae.event_type = 'conversion' THEN 1 END) as total_conversions,
                COUNT(DISTINCT ae.session_id) as unique_sessions,
                COUNT(DISTINCT ae.user_id) as unique_users
            FROM analytics_events ae
            {date_filter}
            AND ae.metadata->>'userLocation' IS NOT NULL
            GROUP BY 
                ae.metadata->>'userLocation'->>'lat',
                ae.metadata->>'userLocation'->>'lng',
                ae.metadata->>'city'
            ORDER BY total_views DESC
            LIMIT 50
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as error:
            print(f'❌ Error getting location analytics: {error}')
            raise error

    @staticmethod
    def get_offer_location_analytics(offer_id, start_date=None, end_date=None):
        """Get location analytics for a specific offer"""
        try:
            date_filter = ""
            params = [offer_id]
            
            if start_date and end_date:
                date_filter = "AND ae.created_at BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            query = f"""
            SELECT 
                ae.metadata->>'userLocation'->>'lat' as latitude,
                ae.metadata->>'userLocation'->>'lng' as longitude,
                COALESCE(ae.metadata->>'city', 'Unknown') as city,
                ae.metadata->>'action' as action_type,
                COUNT(*) as event_count,
                COUNT(CASE WHEN ae.event_type = 'view' THEN 1 END) as views,
                COUNT(CASE WHEN ae.event_type = 'click' THEN 1 END) as clicks,
                COUNT(CASE WHEN ae.event_type = 'conversion' THEN 1 END) as conversions,
                MAX(ae.created_at) as last_interaction
            FROM analytics_events ae
            WHERE ae.offer_id = %s
            {date_filter}
            AND ae.metadata->>'userLocation' IS NOT NULL
            GROUP BY 
                ae.metadata->>'userLocation'->>'lat',
                ae.metadata->>'userLocation'->>'lng',
                ae.metadata->>'city',
                ae.metadata->>'action'
            ORDER BY event_count DESC
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as error:
            print(f'❌ Error getting offer location analytics: {error}')
            raise error

    @staticmethod
    def get_city_performance_analytics(start_date=None, end_date=None):
        """Get analytics performance by city for business insights"""
        try:
            date_filter = ""
            params = []
            
            if start_date and end_date:
                date_filter = "WHERE ae.created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            query = f"""
            SELECT 
                COALESCE(ae.metadata->>'city', 'Unknown') as city,
                COUNT(CASE WHEN ae.event_type = 'view' THEN 1 END) as total_views,
                COUNT(CASE WHEN ae.event_type = 'click' THEN 1 END) as total_clicks,
                COUNT(CASE WHEN ae.event_type = 'conversion' THEN 1 END) as total_conversions,
                COUNT(DISTINCT ae.session_id) as unique_sessions,
                COUNT(DISTINCT ae.user_id) as unique_users,
                COUNT(DISTINCT ae.offer_id) as unique_offers_viewed,
                ROUND(
                    COUNT(CASE WHEN ae.event_type = 'conversion' THEN 1 END)::numeric / 
                    NULLIF(COUNT(CASE WHEN ae.event_type = 'view' THEN 1 END), 0) * 100, 2
                ) as conversion_rate,
                AVG(EXTRACT(EPOCH FROM (ae.created_at - LAG(ae.created_at) OVER (PARTITION BY ae.session_id ORDER BY ae.created_at)))) as avg_session_duration
            FROM analytics_events ae
            {date_filter}
            GROUP BY ae.metadata->>'city'
            ORDER BY total_views DESC
            """
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as error:
            print(f'❌ Error getting city performance analytics: {error}')
            raise error 