from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Company, ESGScore
from scoring.esg_scorer import ESGScorer

app = FastAPI(title="ESG Scoring API")
scorer = ESGScorer()

@app.get("/")
def root():
    return {"message": "ESG Scoring API"}

@app.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).limit(100).all()
    return [{"symbol": c.symbol, "name": c.name, "sector": c.sector} for c in companies]

@app.get("/scores/{symbol}")
def get_company_score(symbol: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.symbol == symbol).first()
    if not company:
        return {"error": "Company not found"}
    
    # Get latest score or calculate new one
    latest_score = db.query(ESGScore).filter(
        ESGScore.company_id == company.id
    ).order_by(ESGScore.score_date.desc()).first()
    
    if not latest_score:
        # Calculate new score
        scores = scorer.calculate_company_score(company.id, db)
        return {
            "symbol": symbol,
            "name": company.name,
            "scores": scores,
            "last_updated": "calculated now"
        }
    
    return {
        "symbol": symbol,
        "scores": {
            "E": latest_score.env_score,
            "S": latest_score.social_score,
            "G": latest_score.governance_score,
            "composite": latest_score.composite_score
        }
    }