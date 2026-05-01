import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings("ignore")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

app = FastAPI(
    title="Financial Report Analyzer",
    description="Summarizes and analyzes sentiment of financial reports using NLP",
    version="1.0.0"
)

# Input schema
class ReportInput(BaseModel):
    ticker: str
    company: str
    period: str
    text: str
# Health check
@app.get("/")
def root():
    return {"status": "Financial Report Analyzer is running"}

# On-demand analyze — lightweight response for deployment
@app.post("/analyze")
def analyze_report(report: ReportInput):
    return {
        "message": "On-demand analysis requires GPU infrastructure.",
        "suggestion": "Use GET /reports to retrieve pre-computed analyses.",
        "ticker": report.ticker,
        "period": report.period
    }

# Get all stored analyses
@app.get("/reports")
def get_reports():
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM report_analysis", conn)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get analysis by ticker
@app.get("/reports/{ticker}")
def get_report_by_ticker(ticker: str):
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                f"SELECT * FROM report_analysis WHERE ticker = '{ticker.upper()}'",
                conn
            )
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No analysis found for {ticker}")
        return df.to_dict(orient="records")
    except HTTPException:
               raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get sentiment summary across all reports
@app.get("/sentiment/summary")
def sentiment_summary():
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                "SELECT ticker, company, sentiment_label, sentiment_score FROM report_analysis",
                conn
            )
        return {
            "total_reports": len(df),
            "positive": len(df[df["sentiment_label"] == "positive"]),
            "negative": len(df[df["sentiment_label"] == "negative"]),
            "neutral": len(df[df["sentiment_label"] == "neutral"]),
            "results": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))