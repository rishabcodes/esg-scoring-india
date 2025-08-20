from sqlalchemy import Column, Integer, String, Text, Float, Date, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True)
    name = Column(String(200))
    sector = Column(String(100))
    
    documents = relationship("Document", back_populates="company")
    scores = relationship("ESGScore", back_populates="company")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    doc_type = Column(String(20))
    content = Column(Text)
    sentiment_score = Column(Float)
    esg_topics = Column(JSON)
    
    company = relationship("Company", back_populates="documents")

class ESGScore(Base):
    __tablename__ = "esg_scores"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    score_date = Column(Date)
    env_score = Column(Float)
    social_score = Column(Float)
    governance_score = Column(Float)
    
    company = relationship("Company", back_populates="scores")