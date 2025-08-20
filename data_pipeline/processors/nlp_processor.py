import pickle
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

class ESGProcessor:
    def __init__(self):
        self.esg_keywords = {
            "E": ["pollution", "carbon", "emission", "waste", "energy", "water"],
            "S": ["employee", "safety", "diversity", "community", "labor"],
            "G": ["board", "audit", "governance", "compliance", "transparency"]
        }
        
    def classify_esg_topics(self, text):
        """Simple keyword-based classification to start"""
        text_lower = text.lower()
        scores = {}
        
        for pillar, keywords in self.esg_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[pillar] = min(score / len(keywords), 1.0)  # Normalize 0-1
        
        return scores
    
    def analyze_sentiment(self, text):
        """Use TextBlob for now, upgrade later"""
        blob = TextBlob(text)
        return blob.sentiment.polarity  # -1 to 1
    
    def detect_controversy(self, text):
        """Simple rule-based for now"""
        controversy_words = ["fine", "penalty", "violation", "lawsuit", "scandal"]
        text_lower = text.lower()
        
        controversy_count = sum(1 for word in controversy_words if word in text_lower)
        return min(controversy_count * 2, 10)  # Scale 0-10