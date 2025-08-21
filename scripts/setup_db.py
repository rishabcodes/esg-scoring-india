#!/usr/bin/env python3
"""
Database setup script for ESG Scoring Engine
Creates tables and initial configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_tables, test_db_connection, engine
from app.models import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_if_not_exists():
    """Create database if it doesn't exist (PostgreSQL only)"""
    try:
        from config import config
        if "postgresql" in config.DATABASE_URL:
            # Extract database name from URL
            db_name = config.DATABASE_URL.split("/")[-1].split("?")[0]
            
            # Connect to postgres database to create our database
            postgres_url = config.DATABASE_URL.replace(f"/{db_name}", "/postgres")
            
            from sqlalchemy import create_engine
            temp_engine = create_engine(postgres_url)
            
            with temp_engine.connect() as conn:
                # Set autocommit mode
                conn = conn.execution_options(autocommit=True)
                
                # Check if database exists
                result = conn.execute(text(
                    f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
                ))
                
                if not result.fetchone():
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database {db_name} already exists")
            
            temp_engine.dispose()
            
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        # Continue anyway, might be using SQLite or database already exists

def setup_indexes():
    """Create additional indexes for performance"""
    try:
        with engine.connect() as conn:
            # Index for document queries by company and date
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_company_date_type 
                ON documents(company_id, published_date, doc_type)
            """))
            
            # Index for ESG scores queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_esg_scores_company_date_desc 
                ON esg_scores(company_id, score_date DESC)
            """))
            
            # Index for company symbol lookup
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_companies_symbol_active 
                ON companies(symbol) WHERE is_active = true
            """))
            
            # Index for document processing status
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_documents_processed_status 
                ON documents(is_processed, created_at)
            """))
            
            conn.commit()
            logger.info("Database indexes created successfully")
            
    except Exception as e:
        logger.warning(f"Index creation failed (might already exist): {e}")

def verify_setup():
    """Verify database setup is correct"""
    try:
        with engine.connect() as conn:
            # Check tables exist
            tables = ['companies', 'documents', 'esg_scores', 'processing_logs']
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                logger.info(f"Table {table}: {count} records")
            
            logger.info("Database verification successful")
            return True
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("Starting database setup...")
    
    # Step 1: Create database if needed
    create_database_if_not_exists()
    
    # Step 2: Test connection
    if not test_db_connection():
        logger.error("Database connection failed. Check your configuration.")
        sys.exit(1)
    
    # Step 3: Create tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)
    
    # Step 4: Setup indexes
    setup_indexes()
    
    # Step 5: Verify setup
    if verify_setup():
        logger.info("✅ Database setup completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Run: python scripts/seed_companies.py")
        logger.info("2. Start API: uvicorn app.main:app --reload")
    else:
        logger.error("❌ Database setup verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()