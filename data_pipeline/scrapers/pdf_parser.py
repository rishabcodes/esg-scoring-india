import PyPDF2
import requests
import io
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.models import Company, Document
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # ESG-related keywords to identify relevant sections
        self.esg_sections = [
            'sustainability', 'environmental', 'social', 'governance',
            'carbon', 'emission', 'waste', 'energy', 'water',
            'employee', 'diversity', 'safety', 'community',
            'board', 'audit', 'compliance', 'risk management',
            'esg', 'csr', 'corporate social responsibility'
        ]
    
    def extract_text_from_pdf_url(self, pdf_url: str) -> Optional[str]:
        """
        Download and extract text from PDF URL
        """
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            response = self.session.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower():
                logger.warning(f"URL doesn't appear to be PDF: {content_type}")
            
            # Read PDF content
            pdf_content = io.BytesIO(response.content)
            text = self.extract_text_from_pdf_bytes(pdf_content)
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.error(f"Error downloading/parsing PDF {pdf_url}: {e}")
            return None
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: io.BytesIO) -> str:
        """
        Extract text from PDF bytes
        """
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_bytes)
            text_content = []
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                
                if page_text.strip():
                    text_content.append(page_text)
            
            full_text = '\n'.join(text_content)
            
            # Clean up text
            full_text = self.clean_extracted_text(full_text)
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', text)
        
        # Remove very short lines (likely headers/footers)
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        return '\n'.join(cleaned_lines)
    
    def extract_esg_sections(self, text: str) -> Dict[str, str]:
        """
        Extract ESG-relevant sections from text
        """
        esg_content = {
            'Environmental': '',
            'Social': '',
            'Governance': '',
            'General': text[:5000]  # First 5000 chars as general content
        }
        
        text_lower = text.lower()
        
        # Simple keyword-based section extraction
        environmental_keywords = ['environment', 'carbon', 'emission', 'pollution', 'waste', 'energy', 'water', 'climate']
        social_keywords = ['employee', 'diversity', 'safety', 'community', 'social', 'welfare', 'training']
        governance_keywords = ['governance', 'board', 'audit', 'compliance', 'risk', 'transparency', 'ethics']
        
        # Split text into paragraphs
        paragraphs = text.split('\n')
        
        for paragraph in paragraphs:
            if len(paragraph) < 50:  # Skip very short paragraphs
                continue
                
            para_lower = paragraph.lower()
            
            # Check for environmental content
            if any(keyword in para_lower for keyword in environmental_keywords):
                esg_content['Environmental'] += paragraph + '\n'
            
            # Check for social content
            elif any(keyword in para_lower for keyword in social_keywords):
                esg_content['Social'] += paragraph + '\n'
            
            # Check for governance content
            elif any(keyword in para_lower for keyword in governance_keywords):
                esg_content['Governance'] += paragraph + '\n'
        
        # Truncate sections to reasonable length
        for key in esg_content:
            if len(esg_content[key]) > 10000:
                esg_content[key] = esg_content[key][:10000] + "...[truncated]"
        
        return esg_content
    
    def find_annual_report_links(self, company_symbol: str) -> List[str]:
        """
        Find annual report download links for a company
        This is a basic implementation - would need company-specific logic
        """
        try:
            # Get company info first
            db = SessionLocal()
            company = db.query(Company).filter(Company.symbol == company_symbol).first()
            db.close()
            
            if not company or not company.website:
                logger.warning(f"No website found for {company_symbol}")
                return []
            
            # Common paths for annual reports
            search_paths = [
                '/investor-relations',
                '/investors',
                '/annual-reports',
                '/financial-reports',
                '/reports'
            ]
            
            pdf_links = []
            base_url = company.website
            
            for path in search_paths:
                try:
                    url = urljoin(base_url, path)
                    response = self.session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find PDF links
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if href.endswith('.pdf') and any(keyword in href.lower() for keyword in ['annual', 'report', '2023', '2024']):
                                full_url = urljoin(url, href)
                                pdf_links.append(full_url)
                
                except Exception as e:
                    logger.debug(f"Error checking {path} for {company_symbol}: {e}")
                    continue
            
            logger.info(f"Found {len(pdf_links)} potential annual report links for {company_symbol}")
            return pdf_links[:3]  # Limit to 3 most recent
            
        except Exception as e:
            logger.error(f"Error finding annual reports for {company_symbol}: {e}")
            return []
    
    def process_company_reports(self, company_symbol: str):
        """
        Process annual reports for a specific company
        """
        db = SessionLocal()
        
        try:
            company = db.query(Company).filter(Company.symbol == company_symbol).first()
            if not company:
                logger.error(f"Company {company_symbol} not found")
                return
            
            # Find report links
            pdf_links = self.find_annual_report_links(company_symbol)
            
            if not pdf_links:
                logger.warning(f"No annual report links found for {company_symbol}")
                return
            
            processed_count = 0
            
            for pdf_url in pdf_links:
                # Check if already processed
                existing = db.query(Document).filter(
                    Document.url == pdf_url,
                    Document.company_id == company.id
                ).first()
                
                if existing:
                    logger.info(f"Report already processed: {pdf_url}")
                    continue
                
                # Extract text from PDF
                full_text = self.extract_text_from_pdf_url(pdf_url)
                
                if not full_text:
                    logger.warning(f"Failed to extract text from {pdf_url}")
                    continue
                
                # Extract ESG sections
                esg_sections = self.extract_esg_sections(full_text)
                
                # Save to database
                document = Document(
                    company_id=company.id,
                    doc_type='annual_report',
                    title=f"Annual Report - {company_symbol}",
                    content=full_text[:50000],  # Limit content size
                    url=pdf_url,
                    source='company_website',
                    published_date=datetime.now().date(),
                    word_count=len(full_text.split()),
                    is_processed=False,
                    created_at=datetime.utcnow()
                )
                
                db.add(document)
                processed_count += 1
                
                logger.info(f"Processed annual report for {company_symbol}: {pdf_url}")
            
            db.commit()
            logger.info(f"Completed processing {processed_count} reports for {company_symbol}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing reports for {company_symbol}: {e}")
            raise
        finally:
            db.close()
    
    def extract_kpis_from_text(self, text: str) -> Dict[str, float]:
        """
        Extract numerical KPIs from text (basic implementation)
        """
        kpis = {}
        
        # Common ESG metrics patterns
        patterns = {
            'carbon_emissions': r'carbon emission[s]?\D*(\d+(?:\.\d+)?)\s*(?:ton|mt|kg)',
            'energy_consumption': r'energy consumption\D*(\d+(?:\.\d+)?)\s*(?:mwh|gwh|kwh)',
            'water_usage': r'water\s+(?:consumption|usage)\D*(\d+(?:\.\d+)?)\s*(?:liters|gallons|m3)',
            'employee_count': r'employee[s]?\D*(\d+(?:,\d+)?)',
            'female_employees': r'(?:female|women)\s+employee[s]?\D*(\d+(?:\.\d+)?)',
            'board_independence': r'independent director[s]?\D*(\d+(?:\.\d+)?)'
        }
        
        text_lower = text.lower()
        
        for metric, pattern in patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    # Take the first match and clean it
                    value = matches[0].replace(',', '')
                    kpis[metric] = float(value)
                except ValueError:
                    continue
        
        return kpis

def main():
    """Main function for testing"""
    parser = PDFParser()
    
    import argparse
    arg_parser = argparse.ArgumentParser(description="PDF Parser for Annual Reports")
    arg_parser.add_argument("--symbol", help="Process reports for specific company symbol")
    arg_parser.add_argument("--url", help="Process specific PDF URL")
    
    args = arg_parser.parse_args()
    
    if args.symbol:
        parser.process_company_reports(args.symbol)
    elif args.url:
        text = parser.extract_text_from_pdf_url(args.url)
        if text:
            print(f"Extracted {len(text)} characters")
            esg_sections = parser.extract_esg_sections(text)
            for section, content in esg_sections.items():
                print(f"\n{section}: {len(content)} characters")
    else:
        print("Please provide --symbol or --url argument")

if __name__ == "__main__":
    main()