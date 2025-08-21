import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://esg_user:esg_pass@localhost:5432/esg_db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # External APIs
    GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    # Data Sources
    NSE_BASE_URL = "https://www.nseindia.com"
    BSE_BASE_URL = "https://www.bseindia.com"
    CPCB_BASE_URL = "https://cpcb.nic.in"
    
    # Scoring Parameters
    DEFAULT_ESG_SCORE = 5.0
    MAX_ESG_SCORE = 10.0
    MIN_ESG_SCORE = 0.0
    TIME_DECAY_FACTOR = 0.9
    
    # Data Processing
    MAX_NEWS_ARTICLES_PER_COMPANY = 100
    NEWS_LOOKBACK_DAYS = 365
    MIN_DOCUMENT_LENGTH = 50
    MAX_DOCUMENT_LENGTH = 50000
    
    # Sector Weights for ESG Scoring
    SECTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
        "Oil & Gas": {"E": 0.5, "S": 0.3, "G": 0.2},
        "Banking": {"E": 0.2, "S": 0.4, "G": 0.4},
        "IT Services": {"E": 0.3, "S": 0.4, "G": 0.3},
        "Pharmaceuticals": {"E": 0.4, "S": 0.4, "G": 0.2},
        "Automotive": {"E": 0.45, "S": 0.35, "G": 0.2},
        "Steel": {"E": 0.5, "S": 0.3, "G": 0.2},
        "Cement": {"E": 0.5, "S": 0.3, "G": 0.2},
        "Telecommunications": {"E": 0.25, "S": 0.35, "G": 0.4},
        "Power": {"E": 0.5, "S": 0.25, "G": 0.25},
        "default": {"E": 0.33, "S": 0.33, "G": 0.34}
    }
    
    # ESG Keywords for Classification
    ESG_KEYWORDS = {
        "Environmental": [
            "carbon emission", "pollution", "waste management", "water conservation",
            "renewable energy", "climate change", "environmental impact", "sustainability",
            "green technology", "carbon footprint", "air quality", "biodiversity",
            "solar power", "wind energy", "recycling", "deforestation"
        ],
        "Social": [
            "employee welfare", "diversity", "workplace safety", "community development",
            "human rights", "labor practices", "social responsibility", "stakeholder engagement",
            "employee training", "health safety", "gender equality", "social impact",
            "workforce diversity", "employee benefits", "community investment"
        ],
        "Governance": [
            "board composition", "transparency", "audit", "compliance", "ethics",
            "risk management", "shareholder rights", "corporate governance", "accountability",
            "disclosure", "internal controls", "regulatory compliance", "executive compensation",
            "board independence", "anti-corruption", "whistleblower protection"
        ]
    }

# Create config instance
config = Config()