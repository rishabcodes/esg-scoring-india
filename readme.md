# ESG Scoring Project - Complete Technical Plan

## Project Overview
Building a production-ready ESG (Environmental, Social, Governance) scoring engine for Indian companies using NLP and real data sources. Target: Top 200-300 NSE/BSE companies with automated scoring based on news sentiment, regulatory filings, and controversy detection.

## Architecture Overview

### Tech Stack
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (primary), Redis (caching)
- **NLP**: scikit-learn, TextBlob, transformers (DistilBERT)
- **Frontend**: Streamlit dashboard
- **Data Sources**: NSE/BSE filings, GDELT news, CPCB data
- **Deployment**: Docker Compose

### System Architecture
```
[Data Sources] → [Scrapers] → [NLP Processing] → [Scoring Engine] → [API] → [Dashboard]
       ↓              ↓             ↓              ↓         ↓         ↓
   NSE/BSE      PDF Parser    ESG Classifier   Score Calc  FastAPI  Streamlit
   GDELT        News Fetch    Sentiment        Time Decay  Endpoints  Charts
   CPCB         Entity Match  Controversy      Sector Wts  Caching   Search
```

## Database Schema

```sql
-- companies table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE,
    name VARCHAR(200),
    sector VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- documents table (news + reports)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    doc_type VARCHAR(20),  -- 'news', 'annual_report', 'regulatory'
    title TEXT,
    content TEXT,
    url VARCHAR(500),
    published_date DATE,
    sentiment_score FLOAT,  -- -1 to 1
    esg_topics JSON,  -- {"E": 0.8, "S": 0.3, "G": 0.1}
    controversy_score INTEGER DEFAULT 0,  -- 0-10
    source VARCHAR(100),  -- 'gdelt', 'nse', 'cpcb'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- esg_scores table
CREATE TABLE esg_scores (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    score_date DATE,
    env_score FLOAT,      -- 0-10
    social_score FLOAT,   -- 0-10
    governance_score FLOAT, -- 0-10
    composite_score FLOAT,  -- 0-10
    explanation JSON,     -- Store calculation details
    data_points_count INTEGER, -- How many docs used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_documents_company_date ON documents(company_id, published_date);
CREATE INDEX idx_esg_scores_company_date ON esg_scores(company_id, score_date);
CREATE INDEX idx_companies_symbol ON companies(symbol);
```

## Project Structure

```
esg-scoring/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── database.py            # SQLAlchemy setup + session management
│   ├── models.py              # SQLAlchemy models
│   └── api/
│       ├── __init__.py
│       ├── companies.py       # Company CRUD endpoints
│       ├── scores.py          # ESG score endpoints
│       └── documents.py       # Document management endpoints
├── data_pipeline/
│   ├── __init__.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── nse_scraper.py     # NSE company data + filings
│   │   ├── bse_scraper.py     # BSE data
│   │   ├── news_scraper.py    # GDELT news fetcher
│   │   ├── cpcb_scraper.py    # Environmental violations
│   │   └── pdf_parser.py      # Extract text from PDFs
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── nlp_processor.py   # All NLP models
│   │   ├── entity_matcher.py  # Match news to companies
│   │   └── data_cleaner.py    # Clean and standardize data
│   └── scheduler.py           # Daily/weekly data updates
├── scoring/
│   ├── __init__.py
│   ├── esg_scorer.py          # Main scoring algorithm
│   ├── weights.py             # Sector-specific weights
│   └── explainer.py           # Score explanation logic
├── dashboard/
│   ├── streamlit_app.py       # Main dashboard
│   ├── components/
│   │   ├── __init__.py
│   │   ├── charts.py          # Plotly charts
│   │   ├── company_search.py  # Search functionality
│   │   └── score_display.py   # Score visualization
│   └── utils.py               # Dashboard utilities
├── scripts/
│   ├── setup_db.py            # Initialize database + tables
│   ├── seed_companies.py      # Load initial company data
│   ├── run_pipeline.py        # Manual pipeline execution
│   ├── backup_db.py           # Database backup
│   └── deploy.py              # Deployment script
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   ├── test_scoring.py        # Scoring logic tests
│   └── test_nlp.py            # NLP processing tests
├── models/                    # Trained ML models
│   ├── esg_classifier.pkl
│   └── entity_matcher.pkl
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Local development setup
├── Dockerfile                 # Production container
├── .env.example              # Environment variables template
└── README.md                 # Project documentation
```

## Data Sources & APIs

### 1. Company Data
- **NSE Listed Companies**: https://www.nseindia.com/market-data/listed-securities
- **BSE Listed Companies**: https://www.bseindia.com/corporates/List_Scrips.aspx
- **Market Cap Data**: Yahoo Finance API / Alpha Vantage

### 2. ESG Documents
- **Annual Reports**: Company websites (automated scraping)
- **BRSR Filings**: NSE/BSE regulatory portals
- **Sustainability Reports**: Company IR pages

### 3. News & Media
- **GDELT Project**: Free news analysis API
  - Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`
  - Filter: `domain:in AND (ESG OR environment OR governance OR sustainability)`
- **Alternative**: NewsAPI, MediaStack (paid tiers)

### 4. Regulatory Data
- **CPCB (Pollution)**: http://cpcb.nic.in/
- **NGT Cases**: https://greentribunal.gov.in/
- **MCA Corporate Filings**: https://www.mca.gov.in/

## NLP Processing Pipeline

### ESG Topic Classification
```python
# Keywords-based approach (Phase 1)
ESG_KEYWORDS = {
    "Environmental": [
        "carbon emission", "pollution", "waste management", "water conservation",
        "renewable energy", "climate change", "environmental impact", "sustainability",
        "green technology", "carbon footprint", "air quality", "biodiversity"
    ],
    "Social": [
        "employee welfare", "diversity", "workplace safety", "community development",
        "human rights", "labor practices", "social responsibility", "stakeholder engagement",
        "employee training", "health safety", "gender equality", "social impact"
    ],
    "Governance": [
        "board composition", "transparency", "audit", "compliance", "ethics",
        "risk management", "shareholder rights", "corporate governance", "accountability",
        "disclosure", "internal controls", "regulatory compliance", "executive compensation"
    ]
}

# Advanced approach (Phase 2)
# Fine-tune DistilBERT on manually labeled ESG content
```

### Sentiment Analysis
- **Phase 1**: TextBlob/VADER for basic sentiment
- **Phase 2**: FinBERT fine-tuned on financial news
- **Output**: Score from -1 (very negative) to +1 (very positive)

### Controversy Detection
```python
CONTROVERSY_INDICATORS = {
    "High Severity": ["fraud", "scandal", "criminal charges", "major violation"],
    "Medium Severity": ["fine", "penalty", "regulatory action", "lawsuit"],
    "Low Severity": ["warning", "notice", "inquiry", "investigation"]
}
```

## Scoring Algorithm

### Pillar Score Calculation
```python
def calculate_pillar_score(company_id, pillar, time_window=365):
    """
    Calculate E, S, or G pillar score for a company
    
    Factors:
    1. Document sentiment (40% weight)
    2. ESG topic relevance (30% weight)
    3. Controversy penalties (20% weight)
    4. Time decay (10% weight)
    """
    
    base_score = 5.0  # Neutral starting point
    
    # Get relevant documents
    docs = get_documents(company_id, pillar, days=time_window)
    
    if not docs:
        return base_score
    
    sentiment_scores = []
    controversy_penalties = []
    
    for doc in docs:
        # Sentiment contribution
        sentiment_impact = (doc.sentiment_score + 1) * 5  # Convert -1,1 to 0,10
        topic_relevance = doc.esg_topics.get(pillar, 0)
        weighted_sentiment = sentiment_impact * topic_relevance
        sentiment_scores.append(weighted_sentiment)
        
        # Controversy penalty
        if doc.controversy_score > 0:
            penalty = doc.controversy_score * 0.5  # Scale down
            controversy_penalties.append(penalty)
    
    # Calculate final score
    avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else base_score
    total_penalty = sum(controversy_penalties)
    
    final_score = max(0, avg_sentiment - total_penalty)
    return min(10, final_score)
```

### Sector Weights
```python
SECTOR_WEIGHTS = {
    "Oil & Gas": {"E": 0.5, "S": 0.3, "G": 0.2},
    "Banking": {"E": 0.2, "S": 0.4, "G": 0.4},
    "IT Services": {"E": 0.3, "S": 0.4, "G": 0.3},
    "Pharmaceuticals": {"E": 0.4, "S": 0.4, "G": 0.2},
    "Manufacturing": {"E": 0.4, "S": 0.35, "G": 0.25},
    "Telecommunications": {"E": 0.25, "S": 0.35, "G": 0.4},
    "default": {"E": 0.33, "S": 0.33, "G": 0.34}
}
```

## API Endpoints

### Core Endpoints
```python
# Company Management
GET    /companies                    # List all companies
GET    /companies/{symbol}          # Get company details
POST   /companies                   # Add new company
PUT    /companies/{symbol}          # Update company

# ESG Scores
GET    /scores/{symbol}             # Latest ESG scores
GET    /scores/{symbol}/history     # Historical scores
GET    /scores/{symbol}/explanation # Score breakdown
POST   /scores/calculate/{symbol}   # Trigger score recalculation

# Documents
GET    /documents/{company_id}      # Company documents
POST   /documents                   # Add new document
GET    /documents/search           # Search documents

# Analytics
GET    /analytics/sector/{sector}   # Sector ESG averages
GET    /analytics/trends           # Market ESG trends
GET    /analytics/controversies    # Recent controversies

# Utilities
POST   /score_text                 # Score arbitrary text
GET    /health                     # System health check
```

### Response Formats
```json
// GET /scores/RELIANCE
{
    "symbol": "RELIANCE",
    "company_name": "Reliance Industries Limited",
    "sector": "Oil & Gas",
    "last_updated": "2025-08-16",
    "scores": {
        "environmental": 6.8,
        "social": 7.2,
        "governance": 8.1,
        "composite": 7.3
    },
    "grade": "B+",
    "data_points": 45,
    "score_trend": "improving"
}

// GET /scores/RELIANCE/explanation
{
    "symbol": "RELIANCE",
    "explanation": {
        "environmental": {
            "score": 6.8,
            "factors": [
                {"factor": "Renewable energy initiatives", "impact": "+1.2"},
                {"factor": "Pollution violations", "impact": "-0.8"},
                {"factor": "Carbon reduction targets", "impact": "+0.6"}
            ],
            "key_documents": 12,
            "controversies": 2
        }
    }
}
```

## Development Checklist

### Phase 1: Foundation (Week 1)
- [ ] **Setup Development Environment**
  - [ ] Install Python 3.9+, PostgreSQL, Redis
  - [ ] Create virtual environment
  - [ ] Install dependencies from requirements.txt
  - [ ] Setup docker-compose for local development

- [ ] **Database Setup**
  - [ ] Create PostgreSQL database
  - [ ] Run schema creation script
  - [ ] Create database connection module
  - [ ] Test database connectivity

- [ ] **Basic Project Structure**
  - [ ] Create all directories as per structure
  - [ ] Setup basic FastAPI app
  - [ ] Create SQLAlchemy models
  - [ ] Setup configuration management

- [ ] **Company Data Pipeline**
  - [ ] Scrape NSE company list (top 100 first)
  - [ ] Create company seeding script
  - [ ] Implement basic entity matching
  - [ ] Test data insertion

### Phase 2: Data Ingestion (Week 2)
- [ ] **News Data Pipeline**
  - [ ] Setup GDELT API integration
  - [ ] Filter news for Indian companies + ESG keywords
  - [ ] Implement news deduplication logic
  - [ ] Store news articles in database

- [ ] **Document Processing**
  - [ ] PDF parsing for annual reports
  - [ ] Text extraction and cleaning
  - [ ] Document chunking for NLP processing
  - [ ] Error handling for malformed documents

- [ ] **Basic NLP Processing**
  - [ ] Implement keyword-based ESG classification
  - [ ] Setup TextBlob sentiment analysis
  - [ ] Rule-based controversy detection
  - [ ] Test NLP pipeline with sample data

### Phase 3: Scoring Engine (Week 3)
- [ ] **Score Calculation Logic**
  - [ ] Implement basic ESG scoring algorithm
  - [ ] Add time decay functionality
  - [ ] Implement sector-specific weights
  - [ ] Create score explanation generator

- [ ] **API Development**
  - [ ] Create all core API endpoints
  - [ ] Add request validation
  - [ ] Implement caching with Redis
  - [ ] Add API documentation (Swagger)

- [ ] **Testing**
  - [ ] Unit tests for scoring logic
  - [ ] API endpoint tests
  - [ ] NLP processing tests
  - [ ] Integration tests

### Phase 4: Dashboard & Enhancement (Week 4)
- [ ] **Streamlit Dashboard**
  - [ ] Company search and selection
  - [ ] ESG score visualization (gauges, charts)
  - [ ] Historical trend analysis
  - [ ] Peer comparison features

- [ ] **Advanced Features**
  - [ ] Batch score calculation
  - [ ] Automated daily updates
  - [ ] Alert system for score changes
  - [ ] Export functionality (CSV, PDF reports)

### Phase 5: Production & Polish (Week 5-6)
- [ ] **Performance Optimization**
  - [ ] Database query optimization
  - [ ] API response caching
  - [ ] Background task processing
  - [ ] Error monitoring and logging

- [ ] **Deployment**
  - [ ] Production Docker setup
  - [ ] Environment configuration
  - [ ] Database backup strategy
  - [ ] Monitoring and health checks

- [ ] **Documentation & Handover**
  - [ ] Complete API documentation
  - [ ] Deployment guide
  - [ ] User manual for dashboard
  - [ ] Code documentation and comments

## Configuration Management

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/esg_db
REDIS_URL=redis://localhost:6379

# API Keys
GDELT_API_KEY=your_key_here
NEWS_API_KEY=your_key_here

# Application
DEBUG=True
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=your_secret_key
API_KEY_ENABLED=False
```

### Sample Config File
```python
# config.py
import os
from typing import Dict, Any

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://esg_user:esg_pass@localhost:5432/esg_db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # External APIs
    GDELT_API_KEY = os.getenv("GDELT_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    # Scoring Parameters
    TIME_DECAY_FACTOR = 0.9
    DEFAULT_SCORE = 5.0
    MAX_SCORE = 10.0
    MIN_SCORE = 0.0
    
    # NLP Settings
    MIN_DOCUMENT_LENGTH = 100
    MAX_DOCUMENT_LENGTH = 10000
    SENTIMENT_THRESHOLD = 0.1
    
    # Sector Weights
    SECTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
        "Oil & Gas": {"E": 0.5, "S": 0.3, "G": 0.2},
        "Banking": {"E": 0.2, "S": 0.4, "G": 0.4},
        "IT Services": {"E": 0.3, "S": 0.4, "G": 0.3},
        "default": {"E": 0.33, "S": 0.33, "G": 0.34}
    }
```

## Deployment Strategy

### Local Development
```bash
# Start services
docker-compose up -d

# Setup database
python scripts/setup_db.py

# Seed initial data
python scripts/seed_companies.py

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run dashboard
streamlit run dashboard/streamlit_app.py --server.port 8501
```

### Production Deployment
- **Option 1**: Docker containers on VPS (DigitalOcean, Linode)
- **Option 2**: Heroku with PostgreSQL addon
- **Option 3**: AWS ECS with RDS PostgreSQL

## Success Metrics
- [ ] **Coverage**: ESG scores for 200+ Indian companies
- [ ] **Data Quality**: 70%+ accuracy on manual ESG score validation
- [ ] **Performance**: API response time < 500ms
- [ ] **Reliability**: 99%+ uptime for scoring system
- [ ] **Usability**: Intuitive dashboard with search and visualization

## Risk Mitigation
- **Data Quality**: Manual validation of 50 companies, feedback loop
- **API Limits**: Implement rate limiting, cache frequently accessed data
- **Model Accuracy**: Start simple (keywords) then iterate to ML models
- **Scale**: Begin with top 100 companies, expand gradually
- **Maintenance**: Automated health checks and monitoring

## Future Enhancements
- Machine learning models for better ESG classification
- Real-time news monitoring and alerts
- Mobile app for ESG score lookup
- Integration with investment platforms
- Multilingual support (Hindi, regional languages)
- ESG portfolio analysis tools