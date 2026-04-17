import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from transformers import BartForConditionalGeneration, BartTokenizer
from transformers import pipeline
import yake
import warnings
warnings.filterwarnings("ignore")

# Database connection
DB_USER = "fraud_user"
DB_PASSWORD = "fraud_pass"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "fraud_db"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

app = FastAPI(
    title="Financial Report Analyzer",
    description="Summarizes and analyzes sentiment of financial reports using NLP",
    version="1.0.0"
)

print("Loading models...")

# Load BART for summarization
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
bart_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

# Load FinBERT for sentiment
sentiment_analyzer = pipeline(
    "text-classification",
    model="ProsusAI/finbert"
)

# Keyword extractor
kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)

print("Models ready")

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

# Analyze a new report
@app.post("/analyze")
def analyze_report(report: ReportInput):
    try:
        # Summarize
        inputs = tokenizer(
            report.text,
            return_tensors="pt",
            max_length=1024,
            truncation=True
        )
        summary_ids = bart_model.generate(
            inputs["input_ids"],
            max_length=150,
            min_length=50,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

        # Sentiment
        words = report.text.split()
        truncated = " ".join(words[:400]) if len(words) > 400 else report.text
        sentiment_result = sentiment_analyzer(truncated, truncation=True, max_length=512)
        sentiment = {
            "label": sentiment_result[0]["label"],
            "score": round(sentiment_result[0]["score"], 4)
        }

        # Keywords
        keywords = [kw[0] for kw in kw_extractor.extract_keywords(report.text)]

        return {
            "ticker": report.ticker,
            "company": report.company,
            "period": report.period,
            "summary": summary,
            "sentiment": sentiment,
            "keywords": keywords
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            df = pd.read_sql("SELECT ticker, company, sentiment_label, sentiment_score FROM report_analysis", conn)
        return {
            "total_reports": len(df),
            "positive": len(df[df["sentiment_label"] == "positive"]),
            "negative": len(df[df["sentiment_label"] == "negative"]),
            "neutral": len(df[df["sentiment_label"] == "neutral"]),
            "results": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))