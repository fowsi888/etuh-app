import json
import openai
import psycopg2.extras
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.database import get_db_connection
from models.tarjous import Tarjous


class AIChat:
    def __init__(self):
        """Initialize AI Chat with database connection"""
        self.openai_client = None
        self.api_key = None
        self.model_name = None
        self.chat_limit = None
        self._load_api_credentials()
        
    def _load_api_credentials(self):
        """Load OpenAI API credentials from database"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get OpenAI credentials including chat_limit
                    cursor.execute("""
                        SELECT api_key, model_name, chat_limit 
                        FROM ai_model_credentials 
                        WHERE service_name = 'OpenAI' 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    
                    result = cursor.fetchone()
                    
                    if result:
                        self.api_key = result[0]
                        self.model_name = result[1] or 'gpt-4o'
                        self.chat_limit = result[2] or 15  # Default to 15 if null
                        
                        # Initialize OpenAI client with modern API
                        self.openai_client = openai.OpenAI(api_key=self.api_key)
                        print(f"✅ OpenAI client initialized with model: {self.model_name}")
                        print(f"✅ API key loaded: {self.api_key[:10]}...")
                        print(f"✅ Chat limit loaded: {self.chat_limit}")
                    else:
                        print("❌ No OpenAI credentials found in database")
                        self.chat_limit = 15  # Default fallback
                        
        except Exception as e:
            print(f"❌ Error loading AI credentials: {e}")
            self.chat_limit = 15  # Default fallback
            import traceback
            traceback.print_exc()
            
    def search_offers_function(self, category: str = None, keywords: str = None, 
                             city: str = None, active_only: bool = True) -> List[Dict]:
        """
        Search offers based on AI-extracted parameters
        This function will be called by GPT-4 when users ask about deals/offers
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    
                    # Build dynamic query with JOIN to get business information
                    # Search in title, description, and keywords columns for offers
                    base_query = """
                        SELECT o.*, b.business_name, b.phone, b.email
                        FROM offers o
                        LEFT JOIN businesses b ON o.business_id = b.id
                        WHERE o.status = 'approved'
                        AND (o.expires_at IS NULL OR o.expires_at >= %s)
                    """
                    params = [datetime.now()]
                    
                    if keywords:
                        base_query += " AND (LOWER(o.title) LIKE LOWER(%s) OR LOWER(o.description) LIKE LOWER(%s) OR LOWER(o.keywords) LIKE LOWER(%s))"
                        search_pattern = f"%{keywords}%"
                        params.extend([search_pattern, search_pattern, search_pattern])
                    
                    if category:
                        base_query += " AND LOWER(o.category) = LOWER(%s)"
                        params.append(category)
                        
                    if city:
                        # Handle various city formats:
                        # 1. Plain text: "koko maa", "Helsinki"  
                        # 2. JSON arrays: ["Koko maa"], ["Helsinki"], ["Espoo,Aura,Helsinki"]
                        # 3. Comma-separated: "Espoo,Aura,Helsinki"
                        base_query += """ AND (
                            LOWER(TRIM(o.city)) = 'koko maa' OR 
                            LOWER(TRIM(o.city)) = LOWER(TRIM(%s)) OR 
                            LOWER(o.city) ~ ('(^|,)\\s*' || LOWER(TRIM(%s)) || '\\s*(,|$)') OR
                            LOWER(o.city) ~ ('\\[".*koko maa.*"\\]') OR
                            LOWER(o.city) ~ ('\\[".*' || LOWER(TRIM(%s)) || '.*"\\]') OR
                            LOWER(o.city) ~ ('".*' || LOWER(TRIM(%s)) || '.*"')
                        )"""
                        params.extend([city, city, city, city])
                        
                    # Order by premium first, then by creation date - ENSURES PREMIUM OFFERS APPEAR FIRST
                    base_query += " ORDER BY o.is_premium DESC, o.created_at DESC LIMIT 10"
                    
                    print(f"🔍 Executing query with city filter (including koko maa and multi-city): {city}")
                    print(f"🔍 Keywords searching in title/description/keywords: {keywords}")
                    print(f"🔍 Query: {base_query}")
                    print(f"🔍 Params: {params}")
                    
                    cursor.execute(base_query, params)
                    offers = cursor.fetchall()
                    
                    print(f"✅ Found {len(offers)} offers")
                    
                    # Convert to list of dictionaries with frontend-compatible field names
                    offer_list = []
                    for offer in offers:
                        offer_dict = dict(offer)
                        
                        # Map database fields to frontend expected fields
                        frontend_offer = {
                            'id': offer_dict.get('id'),
                            'title': offer_dict.get('title'),
                            'description': offer_dict.get('description'),
                            'keywords': offer_dict.get('keywords'),
                            'city': offer_dict.get('city'),
                            'category': offer_dict.get('category'),
                            'address': offer_dict.get('address'),
                            'isPremium': offer_dict.get('is_premium', False),
                            'isNationwide': offer_dict.get('is_nationwide', False),
                            'offerType': offer_dict.get('offer_type'),
                            'cost': float(offer_dict.get('cost')) if offer_dict.get('cost') else None,
                            
                            # Map business fields
                            'businessName': offer_dict.get('business_name'),
                            'merchantName': offer_dict.get('business_name'),
                            'phone': offer_dict.get('phone'),
                            'email': offer_dict.get('email'),
                            
                            # Map date fields
                            'expiresAt': offer_dict.get('expires_at').isoformat() if offer_dict.get('expires_at') else None,
                            'validUntil': offer_dict.get('expires_at').isoformat() if offer_dict.get('expires_at') else None,
                            'startsAt': offer_dict.get('starts_at').isoformat() if offer_dict.get('starts_at') else None,
                            'validFrom': offer_dict.get('starts_at').isoformat() if offer_dict.get('starts_at') else None,
                            'createdAt': offer_dict.get('created_at').isoformat() if offer_dict.get('created_at') else None,
                            'approvedAt': offer_dict.get('approved_at').isoformat() if offer_dict.get('approved_at') else None,
                            
                            # Map image and URL fields
                            'imageUrl': offer_dict.get('image_url'),
                            'imageS3Key': offer_dict.get('image_s3_key'),
                            'offerUrl': offer_dict.get('offer_url'),
                            'website': offer_dict.get('offer_url'),  # Use offer_url as website
                            
                            # Map other fields
                            'status': offer_dict.get('status'),
                            'locationType': offer_dict.get('location_type'),
                            'businessId': offer_dict.get('business_id')
                        }
                        
                        offer_list.append(frontend_offer)
                        
                    return offer_list
            
        except Exception as e:
            print(f"❌ Error searching offers: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_tool_definitions(self) -> List[Dict]:
        """Define the tool schema for OpenAI tools (modern API)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_offers",
                    "description": "Search for deals and offers based on user criteria. Use this when users ask about discounts, deals, offers, or specific products/categories. If you're not sure about the category, don't specify it - search broadly with keywords only.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Product category - ONLY use if you're certain about the category. For unknown items, leave this empty and use keywords instead.",
                                "enum": ["food", "fashion", "electronics", "beauty", "sports", "home", "automotive", "travel", "entertainment", "Ruoka ja juoma", "Muoti", "Teknologia", "Kauneus", "Urheilu ja vapaa-aika", "Koti", "Autot", "Matkailu", "Viihde"]
                            },
                            "keywords": {
                                "type": "string",
                                "description": "Keywords to search in offer title, description, keywords column, and business name (e.g., 'computer', 'pizza', 'shoes', business names)"
                            },
                            "city": {
                                "type": "string",
                                "description": "City name to filter offers by location"
                            },
                            "active_only": {
                                "type": "boolean",
                                "description": "Whether to show only currently active offers",
                                "default": True
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    def process_chat_message(self, user_message: str, user_city: str = None, 
                           language: str = 'en') -> Dict[str, Any]:
        """
        Process user message through OpenAI and handle tool calling
        """
        if not self.openai_client:
            return {
                'success': False,
                'message': 'AI service not available. Please try again later.',
                'offers': []
            }
            
        try:
            # Prepare system message based on language
            if language == 'fi':
                system_message = """Olet Etuhinta AI-avustaja, joka auttaa käyttäjiä löytämään parhaat tarjoukset ja alennukset Suomessa. 
                
TÄRKEÄÄ - OLE TIUKKA NÄISTÄ SÄÄNNÖISTÄ:
1. Tervehdi käyttäjää ystävällisesti suomeksi
2. Jos käyttäjä vain tervehtii (kuten "hei", "moi", "terve"), kysy mitä alennuksia tai tarjouksia he etsivät
3. ETSI TARJOUKSIA KÄYTTÄJÄN KAUPUNGISTA TAI KOKO MAAN TARJOUKSIA:
   - Näytä tarjoukset käyttäjän kaupungista
   - Näytä tarjoukset jotka on merkitty "koko maa" (valtakunnalliset)
   - Näytä tarjoukset jotka sisältävät käyttäjän kaupungin useamman kaupungin tarjouksissa
4. Jos käyttäjä kysyy tarjouksista, käytä search_offers-työkalua NÄIN:
   - Yleisille termeille kuten "vaatteet", "ruoka", "teknologia" - käytä VAIN keywords, ÄLÄ kategoriaa
   - Vain erittäin spesifeille kategorioille käytä category-kenttää
   - Käytä AINA käyttäjän kaupunkia suodattimena
5. KUN LÖYDÄT TARJOUKSIA:
   - Kirjoita lyhyt, ystävällinen viesti jossa kerrot löytäneesi tarjouksia
   - Tarjouskortit näkyvät automaattisesti viestin alapuolella
   - Kannusta käyttäjää klikkaamaan tarjouskortteja saadakseen lisätietoja
6. Jos et löydä tarjouksia käyttäjän kaupungista tai koko maan tarjouksia:
   - Sano: "En löytänyt [hakutermi] tarjouksia tänään [käyttäjän kaupunki]:ssa tai koko maan tarjouksia"
   - Ehdota vaihtoehtoisia hakutermejä samassa kaupungissa

Vastaa aina suomeksi, ole ystävällinen ja auta löytämään parhaat tarjoukset."""
            else:
                system_message = """You are Etuhinta's AI assistant, helping users find the best deals and discounts in Finland.

IMPORTANT - BE STRICT ABOUT THESE RULES:
1. Greet users friendly in English
2. If user just greets (like "hi", "hello"), ask what kind of discounts or offers they're looking for
3. SEARCH OFFERS IN USER'S CITY OR NATIONWIDE OFFERS:
   - Show offers from user's city
   - Show offers marked as "koko maa" (nationwide)
   - Show offers that include user's city in multi-city listings
4. When users ask about offers, use the search_offers tool LIKE THIS:
   - For general terms like "clothes", "food", "technology" - use ONLY keywords, DON'T use category
   - Only use category field for very specific categories
   - ALWAYS use the user's city as filter
5. WHEN YOU FIND OFFERS:
   - Write a short, friendly message telling the user you found offers
   - Offer cards will appear automatically below your message
   - Encourage users to click on the offer cards for more details
6. If no offers found in user's city or nationwide:
   - Say: "I couldn't find [search term] offers today in [user's city] or nationwide offers"
   - Suggest alternative search terms in the same city

Always respond in English and be helpful in finding the best deals."""
            
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Add user city context if available
            if user_city:
                if language == 'fi':
                    messages[0]["content"] += f"\n\nKäyttäjän kaupunki: {user_city}"
                else:
                    messages[0]["content"] += f"\n\nUser's city: {user_city}"
            
            # Call OpenAI with modern tools API
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.get_tool_definitions(),
                tool_choice="auto",
                temperature=0.7,
                max_tokens=500
            )
            
            message = response.choices[0].message
            offers = []
            
            # Handle tool calling
            if message.tool_calls:
                # Process tool calls
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "search_offers":
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Add user city if not specified in function args
                        if user_city and not function_args.get('city'):
                            function_args['city'] = user_city
                            
                        offers = self.search_offers_function(**function_args)
                        
                        # Generate follow-up response with search results
                        if offers:
                            if language == 'fi':
                                follow_up_prompt = f"Löysin {len(offers)} tarjousta. Kirjoita lyhyt, ystävällinen viesti jossa kerrot löytäneesi tarjouksia ja kannustat käyttäjää katsomaan niitä. Pidä viesti lyhyenä ja positiivisena."
                            else:
                                follow_up_prompt = f"I found {len(offers)} offers. Write a short, friendly message telling the user you found offers and encourage them to check them out. Keep the message brief and positive."
                        else:
                            if language == 'fi':
                                follow_up_prompt = f"En löytänyt {function_args.get('keywords', 'tarjouksia')} tarjouksia tänään {function_args.get('city', 'käyttäjän kaupungissa')}:ssa tai koko maan tarjouksia. Ehdota vaihtoehtoisia hakutermejä samassa kaupungissa tai koko maassa."
                            else:
                                follow_up_prompt = f"I couldn't find {function_args.get('keywords', 'offers')} offers today in {function_args.get('city', 'user city')} or nationwide offers. Suggest alternative search terms in the same city or nationwide."
                        
                        # Generate final response with context
                        final_messages = messages + [
                            {"role": "assistant", "content": message.content, "tool_calls": message.tool_calls},
                            {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps({"offers_count": len(offers)})},
                            {"role": "user", "content": follow_up_prompt}
                        ]
                        
                        final_response = self.openai_client.chat.completions.create(
                            model=self.model_name,
                            messages=final_messages,
                            temperature=0.7,
                            max_tokens=300
                        )
                        
                        ai_message = final_response.choices[0].message.content
                        break
            else:
                ai_message = message.content
                
            print(f"🎯 Final AI response:")
            print(f"   Message: {ai_message}")
            print(f"   Offers count: {len(offers)}")
            print(f"   Offers data: {offers}")
                
            return {
                'success': True,
                'message': ai_message,
                'offers': offers
            }
            
        except Exception as e:
            print(f"❌ Error processing chat message: {e}")
            error_msg = "Sorry, I'm having trouble right now. Please try again later." if language == 'en' else "Anteeksi, minulla on teknisiä ongelmia. Yritä myöhemmin uudelleen."
            return {
                'success': False,
                'message': error_msg,
                'offers': []
            } 

    def get_chat_limit(self):
        """Get the current chat limit from database"""
        return getattr(self, 'chat_limit', 15) 