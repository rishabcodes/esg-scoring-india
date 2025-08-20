from datetime import datetime, timedelta
import numpy as np
from config import Config

class ESGScorer:
    def __init__(self):
        self.sector_weights = Config.SECTOR_WEIGHTS
    
    def calculate_company_score(self, company_id, db_session):
        """Calculate ESG score for a company"""
        # Get recent documents (last 12 months)
        cutoff_date = datetime.now() - timedelta(days=365)
        
        documents = db_session.query(Document).filter(
            Document.company_id == company_id,
            Document.published_date >= cutoff_date
        ).all()
        
        if not documents:
            return {"E": 5.0, "S": 5.0, "G": 5.0, "composite": 5.0}  # Neutral
        
        # Calculate pillar scores
        env_scores = []
        social_scores = []
        gov_scores = []
        
        for doc in documents:
            if doc.esg_topics and doc.sentiment_score:
                # Convert sentiment + topic relevance to score
                base_score = (doc.sentiment_score + 1) * 5  # Convert -1,1 to 0,10
                
                if doc.esg_topics.get("E", 0) > 0.3:
                    env_scores.append(base_score * doc.esg_topics["E"])
                if doc.esg_topics.get("S", 0) > 0.3:
                    social_scores.append(base_score * doc.esg_topics["S"])
                if doc.esg_topics.get("G", 0) > 0.3:
                    gov_scores.append(base_score * doc.esg_topics["G"])
        
        # Average scores with time decay (recent news weighted more)
        env_score = np.mean(env_scores) if env_scores else 5.0
        social_score = np.mean(social_scores) if social_scores else 5.0
        gov_score = np.mean(gov_scores) if gov_scores else 5.0
        
        # Get company sector for weighting
        company = db_session.query(Company).get(company_id)
        weights = self.sector_weights.get(company.sector, self.sector_weights["default"])
        
        composite = (
            env_score * weights["E"] + 
            social_score * weights["S"] + 
            gov_score * weights["G"]
        )
        
        return {
            "E": round(env_score, 2),
            "S": round(social_score, 2),
            "G": round(gov_score, 2),
            "composite": round(composite, 2)
        }