#!/usr/bin/env python3

import psycopg2
import psycopg2.extras
from datetime import date
from config.database import get_db_connection

class SimpleAnalytics:
    """Simple analytics that work directly with business_analytics table"""
    
    @staticmethod
    def track_offer_view(offer_id):
        """Track when user views an offer detail (total_views)"""
        return SimpleAnalytics._update_business_analytics(offer_id, 'total_views')
    
    @staticmethod
    def track_offer_click(offer_id):
        """Track when user clicks on an offer (total_clicks)"""
        return SimpleAnalytics._update_business_analytics(offer_id, 'total_clicks')
    
    @staticmethod
    def track_website_conversion(offer_id):
        """Track website conversion (conversion_website + total_conversions)"""
        return SimpleAnalytics._update_business_analytics(offer_id, 'conversion_website', True)
    
    @staticmethod
    def track_call_conversion(offer_id):
        """Track call conversion (conversion_calls + total_conversions)"""
        return SimpleAnalytics._update_business_analytics(offer_id, 'conversion_calls', True)
    
    @staticmethod
    def track_directions_conversion(offer_id):
        """Track directions conversion (conversion_directions + total_conversions)"""
        return SimpleAnalytics._update_business_analytics(offer_id, 'conversion_directions', True)
    
    @staticmethod
    def _update_business_analytics(offer_id, field_name, is_conversion=False):
        """Update business_analytics table directly"""
        try:
            print(f"📊 Tracking {field_name} for offer {offer_id}")
            
            # Get the business_id for this offer
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("SELECT business_id FROM offers WHERE id = %s", (offer_id,))
                    offer_result = cursor.fetchone()
                    
                    if not offer_result:
                        print(f"⚠️ Offer {offer_id} not found")
                        return False
                    
                    business_id = offer_result['business_id']
                    today = date.today()
            
            # Check if record exists for this business and date, create if not
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id FROM business_analytics 
                        WHERE business_id = %s AND date = %s
                    """, (business_id, today))
                    existing_record = cursor.fetchone()
                    
                    if not existing_record:
                        # Create new record with default values
                        cursor.execute("""
                            INSERT INTO business_analytics 
                            (business_id, date, total_views, total_clicks, total_conversions, 
                             total_spent, active_offers, conversion_calls, conversion_directions, 
                             conversion_website, created_at) 
                            VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP)
                        """, (business_id, today))
                        conn.commit()
                        print(f"📝 Created new business_analytics record for business {business_id} on {today}")
            
            # Update the specific field and total conversions if applicable
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    if is_conversion:
                        # Update both the specific conversion field and total_conversions
                        cursor.execute(f"""
                            UPDATE business_analytics 
                            SET {field_name} = {field_name} + 1,
                                total_conversions = total_conversions + 1
                            WHERE business_id = %s AND date = %s
                        """, (business_id, today))
                    else:
                        # Update only the specific field
                        cursor.execute(f"""
                            UPDATE business_analytics 
                            SET {field_name} = {field_name} + 1
                            WHERE business_id = %s AND date = %s
                        """, (business_id, today))
                    
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
                    """, (business_id, business_id, today))
                    
                    conn.commit()
            
            print(f"✅ Updated {field_name} for business {business_id} on {today}")
            return True
                    
        except Exception as error:
            print(f'❌ Error updating business_analytics: {error}')
            import traceback
            traceback.print_exc()
            return False 