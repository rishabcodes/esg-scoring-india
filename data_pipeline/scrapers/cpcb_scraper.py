import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Company, Document
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CPCBScraper:
    def __init__(self):
        self.base_url = config.CPCB_BASE_URL
        self.session = requests.Session()
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def get_pollution_violations(self, state: str = None, limit: int = 100) -> List[Dict]:
        """
        Scrape pollution violation data from CPCB
        Note: CPCB website structure changes frequently, this is a basic implementation
        """
        violations = []
        
        try:
            # CPCB Environmental Compliance data
            # This URL might need adjustment based on current CPCB website structure
            url = f"{self.base_url}/wqm/wqminet.php"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for violation data tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 4:
                        violation_data = {
                            'company_name': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                            'violation_type': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'location': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'date': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'penalty': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'status': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                            'source': 'CPCB'
                        }
                        
                        # Basic filtering
                        if violation_data['company_name'] and len(violation_data['company_name']) > 3:
                            violations.append(violation_data)
                            
                            if len(violations) >= limit:
                                break
            
            logger.info(f"Scraped {len(violations)} pollution violations from CPCB")
            return violations
            
        except Exception as e:
            logger.error(f"Error scraping CPCB violations: {e}")
            return []
    
    def get_air_quality_violations(self, city: str = None) -> List[Dict]:
        """
        Get air quality violations from CPCB
        """
        violations = []
        
        try:
            # Air quality monitoring data
            url = f"{self.base_url}/ccr/caaqm/caaqm_landing_details.php"
            
            params = {}
            if city:
                params['city'] = city
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse air quality data tables
            tables = soup.find_all('table', class_='data-table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:
                    cells = row.find_all('td')
                    
                    if len(cells) >= 3:
                        violation_data = {
                            'location': cells[0].get_text(strip=True),
                            'pollutant': cells[1].get_text(strip=True),
                            'concentration': cells[2].get_text(strip=True),
                            'standard': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'status': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'source': 'CPCB_AirQuality'
                        }
                        
                        violations.append(violation_data)
            
            logger.info(f"Scraped {len(violations)} air quality records")
            return violations
            
        except Exception as e:
            logger.error(f"Error scraping air quality data: {e}")
            return []
    
    def get_water_quality_violations(self) -> List[Dict]:
        """
        Get water quality violations from CPCB
        """
        violations = []
        
        try:
            # Water quality monitoring
            url = f"{self.base_url}/wqm/wqminet.php"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse water quality violation tables
            violation_tables = soup.find_all('table', {'class': ['violation-table', 'data-table']})
            
            for table in violation_tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_all('td')
                    
                    if len(cells) >= 5:
                        violation_data = {
                            'industry_name': cells[0].get_text(strip=True),
                            'location': cells[1].get_text(strip=True),
                            'violation_type': cells[2].get_text(strip=True),
                            'penalty_amount': cells[3].get_text(strip=True),
                            'date': cells[4].get_text(strip=True),
                            'status': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                            'source': 'CPCB_Water'
                        }
                        
                        violations.append(violation_data)
            
            logger.info(f"Scraped {len(violations)} water quality violations")
            return violations
            
        except Exception as e:
            logger.error(f"Error scraping water quality violations: {e}")
            return []
    
    def parse_penalty_amount(self, penalty_text: str) -> float:
        """
        Extract penalty amount from text
        """
        try:
            # Remove currency symbols and extract numbers
            import re
            numbers = re.findall(r'[\d,]+\.?\d*', penalty_text.replace(',', ''))
            
            if numbers:
                amount = float(numbers[0])
                
                # Handle lakhs/crores
                if 'lakh' in penalty_text.lower():
                    amount *= 100000
                elif 'crore' in penalty_text.lower():
                    amount *= 10000000
                
                return amount
            
            return 0.0
            
        except:
            return 0.0
    
    def save_violations_to_db(self, violations: List[Dict]):
        """
        Save violation records to database as documents
        """
        db = SessionLocal()
        
        try:
            saved_count = 0
            
            for violation in violations:
                # Try to match to company
                company_name = violation.get('company_name', violation.get('industry_name', ''))
                
                if not company_name:
                    continue
                
                # Basic company matching
                company_id = self._find_company_by_name(company_name, db)
                
                # Create violation document
                violation_text = self._format_violation_text(violation)
                
                # Check for duplicates
                existing = db.query(Document).filter(
                    Document.content.contains(company_name),
                    Document.doc_type == 'regulatory',
                    Document.source.like('CPCB%')
                ).first()
                
                if existing:
                    continue
                
                document = Document(
                    company_id=company_id,
                    doc_type='regulatory',
                    title=f"CPCB Violation - {company_name}",
                    content=violation_text,
                    url=None,
                    source=violation.get('source', 'CPCB'),
                    published_date=self._parse_violation_date(violation.get('date', '')),
                    language='en',
                    controversy_score=self._calculate_controversy_score(violation),
                    word_count=len(violation_text.split()),
                    is_processed=False,
                    created_at=datetime.utcnow()
                )
                
                db.add(document)
                saved_count += 1
            
            db.commit()
            logger.info(f"Saved {saved_count} violation records to database")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving violations to database: {e}")
            raise
        finally:
            db.close()
    
    def _find_company_by_name(self, company_name: str, db) -> Optional[int]:
        """
        Find company ID by name matching
        """
        try:
            # Direct name match
            company = db.query(Company).filter(
                Company.name.ilike(f"%{company_name}%")
            ).first()
            
            if company:
                return company.id
            
            # Try matching with common company words
            search_terms = company_name.split()
            for term in search_terms:
                if len(term) > 3:  # Avoid short words
                    company = db.query(Company).filter(
                        Company.name.ilike(f"%{term}%")
                    ).first()
                    
                    if company:
                        return company.id
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding company {company_name}: {e}")
            return None
    
    def _format_violation_text(self, violation: Dict) -> str:
        """
        Format violation data as text
        """
        text_parts = []
        
        if violation.get('company_name') or violation.get('industry_name'):
            company = violation.get('company_name', violation.get('industry_name'))
            text_parts.append(f"Company: {company}")
        
        if violation.get('violation_type'):
            text_parts.append(f"Violation Type: {violation['violation_type']}")
        
        if violation.get('location'):
            text_parts.append(f"Location: {violation['location']}")
        
        if violation.get('penalty') or violation.get('penalty_amount'):
            penalty = violation.get('penalty', violation.get('penalty_amount'))
            text_parts.append(f"Penalty: {penalty}")
        
        if violation.get('date'):
            text_parts.append(f"Date: {violation['date']}")
        
        if violation.get('status'):
            text_parts.append(f"Status: {violation['status']}")
        
        return "\n".join(text_parts)
    
    def _parse_violation_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Parse violation date from various formats
        """
        try:
            # Try different date formats
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            return datetime.now().date()
            
        except Exception:
            return datetime.now().date()
    
    def _calculate_controversy_score(self, violation: Dict) -> int:
        """
        Calculate controversy score based on violation severity
        """
        score = 3  # Base score for any violation
        
        # Increase score based on penalty amount
        penalty_text = violation.get('penalty', violation.get('penalty_amount', ''))
        penalty_amount = self.parse_penalty_amount(penalty_text)
        
        if penalty_amount > 10000000:  # > 1 crore
            score += 4
        elif penalty_amount > 1000000:  # > 10 lakh
            score += 3
        elif penalty_amount > 100000:  # > 1 lakh
            score += 2
        
        # Increase score for serious violation types
        violation_type = violation.get('violation_type', '').lower()
        serious_keywords = ['illegal', 'major', 'serious', 'criminal', 'closure']
        
        if any(keyword in violation_type for keyword in serious_keywords):
            score += 2
        
        return min(score, 10)  # Cap at 10
    
    def scrape_all_violations(self):
        """
        Scrape all types of violations
        """
        logger.info("Starting comprehensive CPCB violation scraping")
        
        all_violations = []
        
        # Get different types of violations
        all_violations.extend(self.get_pollution_violations())
        time.sleep(2)
        
        all_violations.extend(self.get_air_quality_violations())
        time.sleep(2)
        
        all_violations.extend(self.get_water_quality_violations())
        
        if all_violations:
            self.save_violations_to_db(all_violations)
            logger.info(f"Completed scraping {len(all_violations)} total violations")
        else:
            logger.warning("No violations data scraped")

def main():
    """Main function for testing"""
    scraper = CPCBScraper()
    
    import argparse
    parser = argparse.ArgumentParser(description="CPCB Violations Scraper")
    parser.add_argument("--all", action="store_true", help="Scrape all violation types")
    parser.add_argument("--pollution", action="store_true", help="Scrape pollution violations only")
    parser.add_argument("--air", action="store_true", help="Scrape air quality violations")
    parser.add_argument("--water", action="store_true", help="Scrape water quality violations")
    
    args = parser.parse_args()
    
    if args.all:
        scraper.scrape_all_violations()
    elif args.pollution:
        violations = scraper.get_pollution_violations()
        scraper.save_violations_to_db(violations)
    elif args.air:
        violations = scraper.get_air_quality_violations()
        scraper.save_violations_to_db(violations)
    elif args.water:
        violations = scraper.get_water_quality_violations()
        scraper.save_violations_to_db(violations)
    else:
        print("Please specify violation type: --all, --pollution, --air, or --water")

if __name__ == "__main__":
    main()