import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
import os
from urllib.parse import quote

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Company, Document
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScrapeer:
    def __init__(self):
        self.gdelt_base_url = config.GDELT_API_BASE
        self.session = requests.Session()
        
        # GDELT doesn't need authentication but has rate limits
        self.session.headers.update({
            'User-Agent': 'ESG-Scoring-Engine/1.0'
        })
    
    def search_company_news(self, company_name: str, symbol: str, days_back: int = 30) -> List[Dict]:
        """
        Search news for a specific company using GDELT
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for GDELT (YYYYMMDDHHMMSS)
            start_str = start_date.strftime("%Y%m%d000000")
            end_str = end_date.strftime("%Y%m%d235959")
            
            # Build search query
            search_terms = [
                f'"{symbol}"',
                f'"{company_name}"'
            ]
            
            # Add ESG keywords
            esg_keywords = [
                "ESG", "environment", "sustainability", "governance", 
                "pollution", "carbon", "social responsibility", "compliance",
                "violation", "fine", "penalty", "audit"
            ]
            
            # Combine search terms
            query = f"({' OR '.join(search_terms)}) AND domain:in AND ({' OR '.join(esg_keywords)})"
            
            params = {
                'query': query,
                'mode': 'artlist',
                'maxrecords': 250,
                'format': 'json',
                'startdatetime': start_str,
                'enddatetime': end_str,
                'sort': 'hybridrel'
            }
            
            response = self.session.get(self.gdelt_base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data:
                for article in data['articles']:
                    article_data = {
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'content': article.get('content', ''),
                        'published_date': self._parse_gdelt_date(article.get('seendate', '')),
                        'source': article.get('domain', ''),
                        'language': article.get('language', 'en')
                    }
                    articles.append(article_data)
            
            logger.info(f"Found {len(articles)} articles for {symbol}")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching news for {symbol}: {e}")
            return []
    
    def _parse_gdelt_date(self, date_str: str) -> Optional[datetime]:
        """Parse GDELT date format"""
        try:
            if len(date_str) >= 8:
                return datetime.strptime(date_str[:8], "%Y%m%d")
            return None
        except:
            return None
    
    def search_esg_news_general(self, days_back: int = 7) -> List[Dict]:
        """
        Search for general ESG news about Indian companies
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime("%Y%m%d000000")
            end_str = end_date.strftime("%Y%m%d235959")
            
            # General ESG query for Indian companies
            query = 'domain:in AND (ESG OR "environmental social governance" OR sustainability OR "carbon emission" OR "pollution fine" OR "regulatory violation" OR "board governance" OR "employee welfare")'
            
            params = {
                'query': query,
                'mode': 'artlist',
                'maxrecords': 500,
                'format': 'json',
                'startdatetime': start_str,
                'enddatetime': end_str,
                'sort': 'hybridrel'
            }
            
            response = self.session.get(self.gdelt_base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data:
                for article in data['articles']:
                    article_data = {
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'content': article.get('content', ''),
                        'published_date': self._parse_gdelt_date(article.get('seendate', '')),
                        'source': article.get('domain', ''),
                        'language': article.get('language', 'en'),
                        'company_id': None  # Will be determined by entity matching
                    }
                    articles.append(article_data)
            
            logger.info(f"Found {len(articles)} general ESG articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching general ESG news: {e}")
            return []
    
    def save_articles_to_db(self, articles: List[Dict], company_id: Optional[int] = None):
        """
        Save articles to database
        """
        db = SessionLocal()
        
        try:
            saved_count = 0
            duplicate_count = 0
            
            for article_data in articles:
                # Check for duplicates by URL
                existing = db.query(Document).filter(
                    Document.url == article_data.get('url', '')
                ).first()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                # Create new document
                document = Document(
                    company_id=company_id or article_data.get('company_id'),
                    doc_type='news',
                    title=article_data.get('title', ''),
                    content=article_data.get('content', ''),
                    url=article_data.get('url', ''),
                    source='gdelt',
                    published_date=article_data.get('published_date'),
                    language=article_data.get('language', 'en'),
                    word_count=len(article_data.get('content', '').split()),
                    is_processed=False,
                    created_at=datetime.utcnow()
                )
                
                db.add(document)
                saved_count += 1
            
            db.commit()
            logger.info(f"Saved {saved_count} articles, {duplicate_count} duplicates skipped")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving articles: {e}")
            raise
        finally:
            db.close()
    
    def scrape_company_news(self, symbol: str, days_back: int = 30):
        """
        Scrape news for a specific company
        """
        db = SessionLocal()
        
        try:
            company = db.query(Company).filter(Company.symbol == symbol).first()
            if not company:
                logger.error(f"Company {symbol} not found")
                return
            
            articles = self.search_company_news(company.name, symbol, days_back)
            
            if articles:
                self.save_articles_to_db(articles, company.id)
                logger.info(f"Completed news scraping for {symbol}")
            else:
                logger.warning(f"No articles found for {symbol}")
                
        finally:
            db.close()
    
    def scrape_all_companies_news(self, days_back: int = 7):
        """
        Scrape news for all active companies
        """
        db = SessionLocal()
        
        try:
            companies = db.query(Company).filter(Company.is_active == True).all()
            
            for i, company in enumerate(companies):
                logger.info(f"Scraping news for {company.symbol} ({i+1}/{len(companies)})")
                
                articles = self.search_company_news(company.name, company.symbol, days_back)
                
                if articles:
                    self.save_articles_to_db(articles, company.id)
                
                # Rate limiting
                time.sleep(2)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1} companies...")
            
            logger.info("Completed news scraping for all companies")
            
        finally:
            db.close()

def main():
    """Main function for testing"""
    scraper = NewsScrapeer()
    
    import argparse
    parser = argparse.ArgumentParser(description="News Scraper")
    parser.add_argument("--symbol", help="Scrape news for specific company symbol")
    parser.add_argument("--all", action="store_true", help="Scrape news for all companies")
    parser.add_argument("--days", type=int, default=30, help="Days back to search")
    
    args = parser.parse_args()
    
    if args.symbol:
        scraper.scrape_company_news(args.symbol, args.days)
    elif args.all:
        scraper.scrape_all_companies_news(args.days)
    else:
        # Test with general ESG news
        articles = scraper.search_esg_news_general(7)
        scraper.save_articles_to_db(articles)

if __name__ == "__main__":
    main()