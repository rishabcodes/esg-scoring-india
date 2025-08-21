import re
import logging
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Company, Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityMatcher:
    def __init__(self):
        self.company_cache = {}
        self.name_variations = {}
        self._load_companies()
    
    def _load_companies(self):
        """Load companies and create lookup variations"""
        db = SessionLocal()
        
        try:
            companies = db.query(Company).filter(Company.is_active == True).all()
            
            for company in companies:
                self.company_cache[company.id] = {
                    'symbol': company.symbol,
                    'name': company.name,
                    'sector': company.sector
                }
                
                # Create name variations for matching
                variations = self._generate_name_variations(company.name, company.symbol)
                for variation in variations:
                    self.name_variations[variation.lower()] = company.id
            
            logger.info(f"Loaded {len(companies)} companies with {len(self.name_variations)} name variations")
            
        finally:
            db.close()
    
    def _generate_name_variations(self, company_name: str, symbol: str) -> List[str]:
        """Generate possible name variations for a company"""
        variations = [symbol, company_name]
        
        # Common company suffixes to remove/add
        suffixes = ['Limited', 'Ltd', 'Corporation', 'Corp', 'Inc', 'Company', 'Co']
        
        # Base name without suffix
        base_name = company_name
        for suffix in suffixes:
            if company_name.endswith(f' {suffix}'):
                base_name = company_name.replace(f' {suffix}', '')
                variations.append(base_name)
                break
        
        # Add variations with different suffixes
        for suffix in ['Ltd', 'Limited']:
            if not base_name.endswith(suffix):
                variations.append(f"{base_name} {suffix}")
        
        # Common abbreviations
        abbreviations = {
            'Infosys': ['INFY'],
            'Tata Consultancy Services': ['TCS'],
            'Reliance Industries': ['RIL'],
            'State Bank of India': ['SBI'],
            'HDFC Bank': ['HDFC'],
            'ICICI Bank': ['ICICI'],
            'Bharti Airtel': ['Airtel'],
            'Oil and Natural Gas Corporation': ['ONGC'],
            'Indian Oil Corporation': ['IOC'],
            'Mahindra & Mahindra': ['M&M', 'Mahindra']
        }
        
        # Add known abbreviations
        for full_name, abbrevs in abbreviations.items():
            if full_name.lower() in company_name.lower():
                variations.extend(abbrevs)
        
        # Add common short forms
        words = base_name.split()
        if len(words) > 2:
            # First two words
            variations.append(' '.join(words[:2]))
            # First and last word
            variations.append(f"{words[0]} {words[-1]}")
        
        return list(set(variations))  # Remove duplicates
    
    def find_company_in_text(self, text: str) -> Optional[Tuple[int, str, float]]:
        """
        Find company mentions in text
        Returns: (company_id, matched_text, confidence_score)
        """
        if not text:
            return None
        
        text_lower = text.lower()
        best_match = None
        highest_confidence = 0.0
        
        for variation, company_id in self.name_variations.items():
            # Exact match (highest confidence)
            if variation in text_lower:
                pattern = r'\b' + re.escape(variation) + r'\b'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    confidence = 0.95
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_match = (company_id, variation, confidence)
                        continue
            
            # Fuzzy matching for partial matches
            words = text_lower.split()
            for i in range(len(words)):
                for j in range(i + 1, min(i + 4, len(words) + 1)):  # Check up to 3-word combinations
                    phrase = ' '.join(words[i:j])
                    similarity = SequenceMatcher(None, variation, phrase).ratio()
                    
                    if similarity > 0.8 and similarity > highest_confidence:
                        highest_confidence = similarity
                        best_match = (company_id, phrase, similarity)
        
        return best_match if highest_confidence > 0.7 else None
    
    def match_news_to_companies(self, limit: int = 100) -> int:
        """
        Process unmatched news articles and assign to companies
        """
        db = SessionLocal()
        
        try:
            # Get unprocessed news documents
            unmatched_docs = db.query(Document).filter(
                Document.doc_type == 'news',
                Document.company_id.is_(None)
            ).limit(limit).all()
            
            matched_count = 0
            
            for doc in unmatched_docs:
                # Try to match using title first (more reliable)
                match = self.find_company_in_text(doc.title or '')
                
                # If no match in title, try content (first 500 chars)
                if not match and doc.content:
                    content_sample = doc.content[:500]
                    match = self.find_company_in_text(content_sample)
                
                if match:
                    company_id, matched_text, confidence = match
                    
                    # Only assign if confidence is high enough
                    if confidence > 0.8:
                        doc.company_id = company_id
                        doc.confidence_score = confidence
                        matched_count += 1
                        
                        company_info = self.company_cache.get(company_id, {})
                        logger.debug(f"Matched '{matched_text}' to {company_info.get('symbol', company_id)} (confidence: {confidence:.2f})")
            
            db.commit()
            logger.info(f"Matched {matched_count} news articles to companies")
            return matched_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error matching news to companies: {e}")
            raise
        finally:
            db.close()
    
    def validate_existing_matches(self) -> Dict[str, int]:
        """
        Validate existing company-document matches
        """
        db = SessionLocal()
        
        try:
            # Get documents that are already matched
            matched_docs = db.query(Document).filter(
                Document.company_id.isnot(None)
            ).limit(200).all()
            
            validation_stats = {
                'total_checked': 0,
                'confirmed_matches': 0,
                'questionable_matches': 0,
                'no_mention_found': 0
            }
            
            for doc in matched_docs:
                validation_stats['total_checked'] += 1
                
                # Check if company is actually mentioned in the document
                company_info = self.company_cache.get(doc.company_id, {})
                company_name = company_info.get('name', '')
                company_symbol = company_info.get('symbol', '')
                
                text_to_check = f"{doc.title or ''} {doc.content[:1000] if doc.content else ''}"
                
                # Look for any mention
                found_mention = False
                for variation in self._generate_name_variations(company_name, company_symbol):
                    if variation.lower() in text_to_check.lower():
                        found_mention = True
                        break
                
                if found_mention:
                    validation_stats['confirmed_matches'] += 1
                else:
                    validation_stats['no_mention_found'] += 1
                    logger.warning(f"Document {doc.id} assigned to {company_symbol} but no mention found")
            
            logger.info(f"Validation complete: {validation_stats}")
            return validation_stats
            
        finally:
            db.close()
    
    def get_company_mentions_stats(self) -> Dict[str, int]:
        """
        Get statistics on company mentions in documents
        """
        db = SessionLocal()
        
        try:
            # Count documents per company
            from sqlalchemy import func
            
            stats = db.query(
                Company.symbol,
                Company.name,
                func.count(Document.id).label('document_count')
            ).outerjoin(Document).group_by(
                Company.id, Company.symbol, Company.name
            ).order_by(func.count(Document.id).desc()).all()
            
            result = {}
            for symbol, name, count in stats:
                result[symbol] = {
                    'name': name,
                    'document_count': count
                }
            
            return result
            
        finally:
            db.close()
    
    def refresh_company_cache(self):
        """Refresh the company cache from database"""
        self.company_cache.clear()
        self.name_variations.clear()
        self._load_companies()
    
    def add_manual_mapping(self, text_pattern: str, company_symbol: str):
        """
        Add manual mapping for specific text patterns
        """
        db = SessionLocal()
        
        try:
            company = db.query(Company).filter(Company.symbol == company_symbol).first()
            if company:
                self.name_variations[text_pattern.lower()] = company.id
                logger.info(f"Added manual mapping: '{text_pattern}' -> {company_symbol}")
            else:
                logger.error(f"Company {company_symbol} not found")
                
        finally:
            db.close()

def main():
    """Main function for testing"""
    matcher = EntityMatcher()
    
    import argparse
    parser = argparse.ArgumentParser(description="Entity Matcher")
    parser.add_argument("--match", action="store_true", help="Match unmatched news articles")
    parser.add_argument("--validate", action="store_true", help="Validate existing matches")
    parser.add_argument("--stats", action="store_true", help="Show company mention statistics")
    parser.add_argument("--text", help="Test matching on specific text")
    
    args = parser.parse_args()
    
    if args.match:
        count = matcher.match_news_to_companies()
        print(f"Matched {count} articles")
    elif args.validate:
        stats = matcher.validate_existing_matches()
        print(f"Validation results: {stats}")
    elif args.stats:
        stats = matcher.get_company_mentions_stats()
        for symbol, info in list(stats.items())[:20]:  # Top 20
            print(f"{symbol}: {info['document_count']} documents")
    elif args.text:
        match = matcher.find_company_in_text(args.text)
        if match:
            company_id, matched_text, confidence = match
            company_info = matcher.company_cache.get(company_id, {})
            print(f"Match: {company_info.get('symbol')} - '{matched_text}' (confidence: {confidence:.2f})")
        else:
            print("No company match found")
    else:
        print("Please specify an action: --match, --validate, --stats, or --text")

if __name__ == "__main__":
    main()