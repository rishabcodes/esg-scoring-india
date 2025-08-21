from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, date

from app.database import get_db, test_db_connection, test_redis_connection
from app.models import Company, Document, ESGScore
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ESG Scoring API",
    description="ESG Scoring Engine for Indian Companies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting ESG Scoring API...")
    
    # Test database connection
    if not test_db_connection():
        logger.error("Database connection failed on startup")
        raise Exception("Database connection failed")
    
    # Test Redis connection (non-critical)
    if test_redis_connection():
        logger.info("Redis connection successful")
    else:
        logger.warning("Redis connection failed - caching disabled")
    
    logger.info("ESG Scoring API started successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    db_status = test_db_connection()
    redis_status = test_redis_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "ESG Scoring API for Indian Companies",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "companies": "/companies",
            "scores": "/scores/{symbol}",
            "search": "/companies/search"
        }
    }

# Companies endpoints
@app.get("/companies")
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sector: Optional[str] = None,
    exchange: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List companies with optional filtering"""
    try:
        query = db.query(Company)
        
        # Apply filters
        if active_only:
            query = query.filter(Company.is_active == True)
        
        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))
        
        if exchange:
            query = query.filter(Company.exchange == exchange.upper())
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        companies = query.offset(skip).limit(limit).all()
        
        return {
            "companies": [
                {
                    "symbol": company.symbol,
                    "name": company.name,
                    "sector": company.sector,
                    "exchange": company.exchange,
                    "is_active": company.is_active
                }
                for company in companies
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/companies/{symbol}")
async def get_company(symbol: str, db: Session = Depends(get_db)):
    """Get company details by symbol"""
    try:
        company = db.query(Company).filter(Company.symbol == symbol.upper()).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get document count
        doc_count = db.query(Document).filter(Document.company_id == company.id).count()
        
        # Get latest ESG score
        latest_score = db.query(ESGScore).filter(
            ESGScore.company_id == company.id
        ).order_by(ESGScore.score_date.desc()).first()
        
        return {
            "symbol": company.symbol,
            "name": company.name,
            "sector": company.sector,
            "industry": company.industry,
            "exchange": company.exchange,
            "market_cap": company.market_cap,
            "website": company.website,
            "is_active": company.is_active,
            "documents_count": doc_count,
            "latest_esg_score": {
                "environmental": latest_score.environmental_score if latest_score else None,
                "social": latest_score.social_score if latest_score else None,
                "governance": latest_score.governance_score if latest_score else None,
                "composite": latest_score.composite_score if latest_score else None,
                "score_date": latest_score.score_date.isoformat() if latest_score else None
            } if latest_score else None,
            "created_at": company.created_at.isoformat(),
            "updated_at": company.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/companies/search")
async def search_companies(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search companies by name or symbol"""
    try:
        search_term = f"%{q}%"
        
        companies = db.query(Company).filter(
            (Company.name.ilike(search_term)) | 
            (Company.symbol.ilike(search_term))
        ).filter(Company.is_active == True).limit(limit).all()
        
        return {
            "query": q,
            "results": [
                {
                    "symbol": company.symbol,
                    "name": company.name,
                    "sector": company.sector,
                    "exchange": company.exchange
                }
                for company in companies
            ],
            "count": len(companies)
        }
        
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ESG Scores endpoints
@app.get("/scores/{symbol}")
async def get_esg_scores(symbol: str, db: Session = Depends(get_db)):
    """Get latest ESG scores for a company"""
    try:
        company = db.query(Company).filter(Company.symbol == symbol.upper()).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get latest score
        latest_score = db.query(ESGScore).filter(
            ESGScore.company_id == company.id
        ).order_by(ESGScore.score_date.desc()).first()
        
        if not latest_score:
            return {
                "symbol": symbol.upper(),
                "company_name": company.name,
                "message": "No ESG scores available yet",
                "scores": None
            }
        
        return {
            "symbol": symbol.upper(),
            "company_name": company.name,
            "sector": company.sector,
            "last_updated": latest_score.score_date.isoformat(),
            "scores": {
                "environmental": round(latest_score.environmental_score, 2),
                "social": round(latest_score.social_score, 2),
                "governance": round(latest_score.governance_score, 2),
                "composite": round(latest_score.composite_score, 2)
            },
            "components": {
                "sentiment": latest_score.sentiment_component,
                "controversy": latest_score.controversy_component,
                "disclosure": latest_score.disclosure_component
            },
            "metadata": {
                "data_points": latest_score.data_points_count,
                "confidence": latest_score.confidence_level,
                "calculation_method": latest_score.calculation_method
            },
            "explanation": latest_score.score_explanation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ESG scores for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Statistics endpoint
@app.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        total_companies = db.query(Company).filter(Company.is_active == True).count()
        total_documents = db.query(Document).count()
        total_scores = db.query(ESGScore).count()
        
        # Sector breakdown
        from sqlalchemy import func
        sector_counts = db.query(
            Company.sector,
            func.count(Company.id).label('count')
        ).filter(Company.is_active == True).group_by(Company.sector).all()
        
        return {
            "total_companies": total_companies,
            "total_documents": total_documents,
            "total_esg_scores": total_scores,
            "sectors": [
                {"sector": sector, "count": count}
                for sector, count in sector_counts
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG
    )