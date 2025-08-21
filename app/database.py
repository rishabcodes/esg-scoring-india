from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import redis
from config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Engine
engine = create_engine(
    config.DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
        "options": "-c timezone=utc"
    } if "sqlite" in config.DATABASE_URL else {},
    echo=config.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis Connection
try:
    redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

def get_db() -> Session:
    """
    Database dependency for FastAPI endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis():
    """
    Redis dependency for FastAPI endpoints
    """
    return redis_client

def create_tables():
    """
    Create all database tables
    """
    try:
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def drop_tables():
    """
    Drop all database tables (use with caution)
    """
    try:
        from app.models import Base
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise

def test_db_connection():
    """
    Test database connection
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def test_redis_connection():
    """
    Test Redis connection
    """
    try:
        if redis_client:
            redis_client.ping()
            logger.info("Redis connection test successful")
            return True
        else:
            logger.warning("Redis client not available")
            return False
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

# Cache utilities
class CacheManager:
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    def get(self, key: str):
        """Get value from cache"""
        if not self.redis:
            return None
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache with TTL"""
        if not self.redis:
            return False
        try:
            return self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis:
            return False
        try:
            return self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

# Global cache manager instance
cache_manager = CacheManager(redis_client)