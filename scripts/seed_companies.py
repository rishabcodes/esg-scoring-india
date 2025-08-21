#!/usr/bin/env python3
"""
Seed script to populate initial company data
Loads Nifty 100 companies as starting dataset
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Company
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nifty 100 companies data (subset for initial development)
INITIAL_COMPANIES = [
    # Technology
    {"symbol": "TCS", "name": "Tata Consultancy Services Limited", "sector": "IT Services", "exchange": "NSE"},
    {"symbol": "INFY", "name": "Infosys Limited", "sector": "IT Services", "exchange": "NSE"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Limited", "sector": "IT Services", "exchange": "NSE"},
    {"symbol": "WIPRO", "name": "Wipro Limited", "sector": "IT Services", "exchange": "NSE"},
    {"symbol": "TECHM", "name": "Tech Mahindra Limited", "sector": "IT Services", "exchange": "NSE"},
    
    # Banking & Financial Services
    {"symbol": "HDFCBANK", "name": "HDFC Bank Limited", "sector": "Banking", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Limited", "sector": "Banking", "exchange": "NSE"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking", "exchange": "NSE"},
    {"symbol": "AXISBANK", "name": "Axis Bank Limited", "sector": "Banking", "exchange": "NSE"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Limited", "sector": "Banking", "exchange": "NSE"},
    
    # Oil & Gas
    {"symbol": "RELIANCE", "name": "Reliance Industries Limited", "sector": "Oil & Gas", "exchange": "NSE"},
    {"symbol": "ONGC", "name": "Oil and Natural Gas Corporation Limited", "sector": "Oil & Gas", "exchange": "NSE"},
    {"symbol": "IOC", "name": "Indian Oil Corporation Limited", "sector": "Oil & Gas", "exchange": "NSE"},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corporation Limited", "sector": "Oil & Gas", "exchange": "NSE"},
    
    # Pharmaceuticals
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Limited", "sector": "Pharmaceuticals", "exchange": "NSE"},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Limited", "sector": "Pharmaceuticals", "exchange": "NSE"},
    {"symbol": "CIPLA", "name": "Cipla Limited", "sector": "Pharmaceuticals", "exchange": "NSE"},
    {"symbol": "BIOCON", "name": "Biocon Limited", "sector": "Pharmaceuticals", "exchange": "NSE"},
    
    # Automotive
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Limited", "sector": "Automotive", "exchange": "NSE"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Limited", "sector": "Automotive", "exchange": "NSE"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Limited", "sector": "Automotive", "exchange": "NSE"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Limited", "sector": "Automotive", "exchange": "NSE"},
    
    # Steel & Metals
    {"symbol": "TATASTEEL", "name": "Tata Steel Limited", "sector": "Steel", "exchange": "NSE"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Limited", "sector": "Steel", "exchange": "NSE"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Limited", "sector": "Steel", "exchange": "NSE"},
    {"symbol": "COALINDIA", "name": "Coal India Limited", "sector": "Steel", "exchange": "NSE"},
    
    # Cement
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Limited", "sector": "Cement", "exchange": "NSE"},
    {"symbol": "SHREECEM", "name": "Shree Cement Limited", "sector": "Cement", "exchange": "NSE"},
    {"symbol": "ACC", "name": "ACC Limited", "sector": "Cement", "exchange": "NSE"},
    
    # Power
    {"symbol": "NTPC", "name": "NTPC Limited", "sector": "Power", "exchange": "NSE"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Limited", "sector": "Power", "exchange": "NSE"},
    {"symbol": "ADANIGREEN", "name": "Adani Green Energy Limited", "sector": "Power", "exchange": "NSE"},
    
    # Telecommunications
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Limited", "sector": "Telecommunications", "exchange": "NSE"},
    {"symbol": "IDEA", "name": "Vodafone Idea Limited", "sector": "Telecommunications", "exchange": "NSE"},
    
    # Consumer Goods
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Limited", "sector": "Consumer Goods", "exchange": "NSE"},
    {"symbol": "ITC", "name": "ITC Limited", "sector": "Consumer Goods", "exchange": "NSE"},
    {"symbol": "NESTLEIND", "name": "Nestle India Limited", "sector": "Consumer Goods", "exchange": "NSE"},
    
    # Adani Group (High ESG attention)
    {"symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Limited", "sector": "Infrastructure", "exchange": "NSE"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Limited", "sector": "Infrastructure", "exchange": "NSE"},
    {"symbol": "ADANITRANS", "name": "Adani Transmission Limited", "sector": "Power", "exchange": "NSE"},
]

def seed_companies():
    """Insert initial company data into database"""
    db = SessionLocal()
    
    try:
        # Check if companies already exist
        existing_count = db.query(Company).count()
        if existing_count > 0:
            logger.info(f"Database already has {existing_count} companies")
            response = input("Do you want to add more companies anyway? (y/n): ")
            if response.lower() != 'y':
                logger.info("Skipping company seeding")
                return
        
        companies_added = 0
        companies_skipped = 0
        
        for company_data in INITIAL_COMPANIES:
            # Check if company already exists
            existing = db.query(Company).filter(Company.symbol == company_data["symbol"]).first()
            
            if existing:
                logger.info(f"Skipping {company_data['symbol']} - already exists")
                companies_skipped += 1
                continue
            
            # Create new company
            company = Company(
                symbol=company_data["symbol"],
                name=company_data["name"],
                sector=company_data["sector"],
                exchange=company_data["exchange"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(company)
            companies_added += 1
            logger.info(f"Added company: {company_data['symbol']} - {company_data['name']}")
        
        # Commit all changes
        db.commit()
        
        logger.info(f"✅ Company seeding completed!")
        logger.info(f"   Added: {companies_added} companies")
        logger.info(f"   Skipped: {companies_skipped} companies")
        logger.info(f"   Total in database: {db.query(Company).count()} companies")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding companies: {e}")
        raise
    finally:
        db.close()

def list_companies():
    """List all companies in database"""
    db = SessionLocal()
    
    try:
        companies = db.query(Company).order_by(Company.sector, Company.symbol).all()
        
        if not companies:
            logger.info("No companies found in database")
            return
        
        logger.info(f"\n📊 Companies in Database ({len(companies)} total):")
        logger.info("=" * 80)
        
        current_sector = None
        for company in companies:
            if company.sector != current_sector:
                current_sector = company.sector
                logger.info(f"\n🏢 {current_sector}:")
                logger.info("-" * 40)
            
            logger.info(f"  {company.symbol:<12} | {company.name}")
        
        # Sector summary
        from sqlalchemy import func
        sector_counts = db.query(
            Company.sector,
            func.count(Company.id).label('count')
        ).group_by(Company.sector).order_by(Company.sector).all()
        
        logger.info(f"\n📈 Sector Summary:")
        logger.info("-" * 30)
        for sector, count in sector_counts:
            logger.info(f"  {sector:<20}: {count} companies")
            
    finally:
        db.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed companies database")
    parser.add_argument("--list", action="store_true", help="List existing companies")
    args = parser.parse_args()
    
    if args.list:
        list_companies()
    else:
        seed_companies()

if __name__ == "__main__":
    main()