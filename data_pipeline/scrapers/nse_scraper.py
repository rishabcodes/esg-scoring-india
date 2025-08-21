import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Company
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NSEScraper:
    def __init__(self):
        self.base_url = config.NSE_BASE_URL
        self.session = requests.Session()
        
        # NSE requires specific headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Get initial cookies
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session with NSE cookies"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            logger.info("NSE session initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize NSE session: {e}")
    
    def get_nifty_100_companies(self) -> List[Dict]:
        """
        Fetch Nifty 100 companies list
        """
        try:
            # NSE API endpoint for Nifty 100
            url = f"{self.base_url}/api/equity-stockIndices?index=NIFTY%20100"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            companies = []
            
            if 'data' in data:
                for stock in data['data']:
                    company_info = {
                        'symbol': stock.get('symbol', ''),
                        'name': stock.get('companyName', ''),
                        'sector': stock.get('industry', ''),
                        'series': stock.get('series', ''),
                        'market_cap': None,  # Not available in this endpoint
                        'isin': stock.get('isin', ''),
                        'exchange': 'NSE'
                    }
                    companies.append(company_info)
            
            logger.info(f"Fetched {len(companies)} companies from Nifty 100")
            return companies
            
        except Exception as e:
            logger.error(f"Error fetching Nifty 100 companies: {e}")
            return []
    
    def get_nifty_500_companies(self) -> List[Dict]:
        """
        Fetch Nifty 500 companies list
        """
        try:
            url = f"{self.base_url}/api/equity-stockIndices?index=NIFTY%20500"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            companies = []
            
            if 'data' in data:
                for stock in data['data']:
                    company_info = {
                        'symbol': stock.get('symbol', ''),
                        'name': stock.get('companyName', ''),
                        'sector': stock.get('industry', ''),
                        'series': stock.get('series', ''),
                        'market_cap': None,
                        'isin': stock.get('isin', ''),
                        'exchange': 'NSE'
                    }
                    companies.append(company_info)
            
            logger.info(f"Fetched {len(companies)} companies from Nifty 500")
            return companies
            
        except Exception as e:
            logger.error(f"Error fetching Nifty 500 companies: {e}")
            return []
    
    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed company information
        """
        try:
            url = f"{self.base_url}/api/quote-equity?symbol={symbol}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'info' in data:
                info = data['info']
                company_info = {
                    'symbol': symbol,
                    'name': info.get('companyName', ''),
                    'industry': info.get('industry', ''),
                    'sector': info.get('sector', ''),
                    'website': info.get('website', ''),
                    'isin': info.get('isin', ''),
                    'market_cap': data.get('priceInfo', {}).get('basePrice', 0) * info.get('totalTradedVolume', 0)
                }
                return company_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching company info for {symbol}: {e}")
            return None
    
    def get_annual_reports_links(self, symbol: str) -> List[Dict]:
        """
        Get annual reports download links for a company
        This is a placeholder - NSE doesn't directly provide these
        """
        try:
            # This would require scraping company-specific pages
            # For now, return empty list
            logger.info(f"Annual reports scraping not implemented for {symbol}")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching annual reports for {symbol}: {e}")
            return []
    
    def update_companies_in_db(self, companies: List[Dict]):
        """
        Update company information in database
        """
        db = SessionLocal()
        
        try:
            updated_count = 0
            added_count = 0
            
            for company_data in companies:
                symbol = company_data.get('symbol', '').strip()
                if not symbol:
                    continue
                
                # Check if company exists
                existing = db.query(Company).filter(Company.symbol == symbol).first()
                
                if existing:
                    # Update existing company
                    existing.name = company_data.get('name', existing.name)
                    existing.sector = company_data.get('sector', existing.sector)
                    existing.industry = company_data.get('industry', existing.industry)
                    existing.website = company_data.get('website', existing.website)
                    existing.isin = company_data.get('isin', existing.isin)
                    existing.market_cap = company_data.get('market_cap', existing.market_cap)
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                    
                else:
                    # Add new company
                    new_company = Company(
                        symbol=symbol,
                        name=company_data.get('name', ''),
                        sector=company_data.get('sector', ''),
                        industry=company_data.get('industry', ''),
                        website=company_data.get('website', ''),
                        isin=company_data.get('isin', ''),
                        market_cap=company_data.get('market_cap'),
                        exchange='NSE',
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_company)
                    added_count += 1
            
            db.commit()
            logger.info(f"Database updated: {added_count} added, {updated_count} updated")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating database: {e}")
            raise
        finally:
            db.close()
    
    def scrape_and_update(self, index_type: str = "nifty100"):
        """
        Main method to scrape companies and update database
        """
        logger.info(f"Starting NSE scraping for {index_type}")
        
        if index_type.lower() == "nifty100":
            companies = self.get_nifty_100_companies()
        elif index_type.lower() == "nifty500":
            companies = self.get_nifty_500_companies()
        else:
            logger.error(f"Unknown index type: {index_type}")
            return
        
        if companies:
            # Get detailed info for each company (limited to avoid rate limiting)
            detailed_companies = []
            for i, company in enumerate(companies[:50]):  # Limit to first 50 for testing
                symbol = company['symbol']
                detailed_info = self.get_company_info(symbol)
                
                if detailed_info:
                    # Merge basic and detailed info
                    company.update(detailed_info)
                
                detailed_companies.append(company)
                
                # Rate limiting
                time.sleep(0.5)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1} companies...")
            
            # Update database
            self.update_companies_in_db(detailed_companies)
            logger.info("NSE scraping completed successfully")
        else:
            logger.warning("No companies found to update")

def main():
    """Main function for testing"""
    scraper = NSEScraper()
    
    import argparse
    parser = argparse.ArgumentParser(description="NSE Companies Scraper")
    parser.add_argument("--index", choices=["nifty100", "nifty500"], default="nifty100")
    args = parser.parse_args()
    
    scraper.scrape_and_update(args.index)

if __name__ == "__main__":
    main()