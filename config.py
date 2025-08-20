import os

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/esg_db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Keys
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # For news sources
    
    # NLP Models
    ESG_MODEL_PATH = "models/esg_classifier.pkl"
    
    # Scoring weights
    SECTOR_WEIGHTS = {
        "Banking": {"E": 0.2, "S": 0.4, "G": 0.4},
        "Oil & Gas": {"E": 0.5, "S": 0.3, "G": 0.2},
        "IT": {"E": 0.3, "S": 0.4, "G": 0.3},
        "default": {"E": 0.33, "S": 0.33, "G": 0.34}
    }