from sqlalchemy import Column, Integer, String, Text, Float, Date, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(300), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    exchange = Column(String(10), nullable=True)  # NSE, BSE
    isin = Column(String(20), nullable=True)
    website = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    esg_scores = relationship("ESGScore", back_populates="company", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    doc_type = Column(String(30), nullable=False)  # 'news', 'annual_report', 'regulatory', 'brsr'
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    source = Column(String(100), nullable=True)  # 'gdelt', 'nse', 'bse', 'cpcb', 'ngt'
    published_date = Column(Date, nullable=True, index=True)
    processed_date = Column(DateTime, default=datetime.utcnow)
    
    # NLP Analysis Results
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    esg_relevance = Column(JSON, nullable=True)  # {"E": 0.8, "S": 0.3, "G": 0.1}
    controversy_score = Column(Integer, default=0)  # 0-10
    language = Column(String(10), default="en")
    
    # Metadata
    word_count = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)  # NLP confidence
    is_processed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="documents")

class ESGScore(Base):
    __tablename__ = "esg_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)
    
    # ESG Pillar Scores (0-10)
    environmental_score = Column(Float, nullable=False)
    social_score = Column(Float, nullable=False)
    governance_score = Column(Float, nullable=False)
    composite_score = Column(Float, nullable=False)
    
    # Score Components
    sentiment_component = Column(Float, nullable=True)
    controversy_component = Column(Float, nullable=True)
    disclosure_component = Column(Float, nullable=True)
    
    # Metadata
    data_points_count = Column(Integer, default=0)
    score_explanation = Column(JSON, nullable=True)  # Detailed breakdown
    calculation_method = Column(String(50), default="v1")
    confidence_level = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="esg_scores")

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    process_type = Column(String(50), nullable=False)  # 'news_scraping', 'scoring', 'nlp_processing'
    status = Column(String(20), nullable=False)  # 'started', 'completed', 'failed'
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)