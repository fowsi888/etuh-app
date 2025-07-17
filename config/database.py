import psycopg2
import psycopg2.extras
import psycopg2.pool
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration - Updated to use remote PostgreSQL server
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '13.50.146.127'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'etuhinta'),
    'user': os.getenv('DB_USER', 'fowsi'),
    'password': os.getenv('DB_PASSWORD', 'AnwaR.88'),
}

# Connection pool
connection_pool = None

def init_db():
    """Initialize database connection pool"""
    global connection_pool
    
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            **DB_CONFIG
        )
        print("✅ Database connection pool created successfully")
        
        # Test connection
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"📊 Connected to PostgreSQL: {version[0]}")
                
    except Exception as error:
        print(f"❌ Error creating connection pool: {error}")
        raise error

@contextmanager
def get_db_connection():
    """Get database connection from pool with context manager"""
    if connection_pool is None:
        raise Exception("Database connection pool not initialized")
    
    connection = None
    try:
        connection = connection_pool.getconn()
        yield connection
    except Exception as error:
        if connection:
            connection.rollback()
        raise error
    finally:
        if connection:
            connection_pool.putconn(connection)

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount

def execute_query_dict(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query and return results as dictionaries"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return dict(cursor.fetchone()) if cursor.fetchone() else None
            elif fetch_all:
                return [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                return cursor.rowcount

def close_db():
    """Close database connection pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("🔒 Database connection pool closed") 