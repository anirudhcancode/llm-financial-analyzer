import os
import json
from datetime import date
from typing import Optional
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

app = FastAPI(
    title="LLM Financial Intelligence Platform",
    description="NLP sentiment analysis, historical trends, and ML predictions for 10 major companies",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

COMPANIES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla Inc.",
    "PLTR": "Palantir Technologies",
    "SNOW": "Snowflake Inc.",
    "DDOG": "Datadog Inc.",
    "MDB":  "MongoDB Inc.",
}

@app.get("/")
def root():
    return {
        "name": "LLM Financial Intelligence Platform",
        "version": "2.0.0",
        "companies": list(COMPANIES.keys()),
        "endpoints": [
            "/reports",
            "/reports/{ticker}",
            "/sentiment/summary",
            "/stock/{ticker}/history",
            "/stock/{ticker}/events",
            "/stock/{ticker}/prediction",
            "/stock/{ticker}/earnings",
            "/correlation",
            "/companies"
        ]
    }

@app.get("/companies")
def get_companies():
    return {"companies": COMPANIES}

# ── Existing NLP endpoints ──

@app.get("/reports")
def get_reports():
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM report_analysis ORDER BY created_at DESC", conn)
    return {"count": len(df), "reports": df.to_dict(orient="records")}

@app.get("/reports/{ticker}")
def get_report(ticker: str):
    ticker = ticker.upper()
    with engine.connect() as conn:
        df = pd.read_sql(
            f"SELECT * FROM report_analysis WHERE ticker = '{ticker}'", conn
        )
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No report found for {ticker}")
    return df.to_dict(orient="records")[0]

@app.get("/sentiment/summary")
def sentiment_summary():
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM report_analysis", conn)
    if df.empty:
        raise HTTPException(status_code=404, detail="No reports found")
    summary = {
        "total_reports": len(df),
        "positive": int((df['sentiment_label'] == 'positive').sum()),
        "negative": int((df['sentiment_label'] == 'negative').sum()),
        "neutral": int((df['sentiment_label'] == 'neutral').sum()),
        "most_positive": df.loc[df['sentiment_score'].idxmax(), 'ticker'] if 'sentiment_score' in df.columns else None,
        "most_negative": df.loc[df['sentiment_score'].idxmin(), 'ticker'] if 'sentiment_score' in df.columns else None,
        "reports": df[['ticker', 'company', 'sentiment_label', 'sentiment_score']].to_dict(orient="records")
    }
    return summary

# ── New stock history endpoints ──

@app.get("/stock/{ticker}/history")
def stock_history(ticker: str, days: int = 365):
    ticker = ticker.upper()
    if ticker not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""SELECT date, close, volume, daily_return, volatility_30d,
                momentum_30d, momentum_90d
                FROM price_metrics
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT {days}""",
            conn
        )
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")
    df['date'] = df['date'].astype(str)
    df = df.sort_values('date')
    return {
        "ticker": ticker,
        "company": COMPANIES[ticker],
        "days": len(df),
        "latest_price": round(float(df['close'].iloc[-1]), 2),
        "price_change_30d": round(float(df['momentum_30d'].iloc[-1] or 0), 2),
        "price_change_90d": round(float(df['momentum_90d'].iloc[-1] or 0), 2),
        "volatility_30d": round(float(df['volatility_30d'].iloc[-1] or 0), 2),
        "history": df.to_dict(orient="records")
    }

@app.get("/stock/{ticker}/events")
def stock_events(ticker: str):
    ticker = ticker.upper()
    if ticker not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""SELECT date, event_type, price_change_pct, close_price, description
                FROM market_events
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 50""",
            conn
        )
    df['date'] = df['date'].astype(str)
    return {
        "ticker": ticker,
        "company": COMPANIES[ticker],
        "total_major_events": len(df),
        "events": df.to_dict(orient="records")
    }

@app.get("/stock/{ticker}/earnings")
def stock_earnings(ticker: str):
    ticker = ticker.upper()
    if ticker not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    with engine.connect() as conn:
        earnings = pd.read_sql(
            f"""SELECT period, period_date, eps_actual, eps_estimate,
                eps_surprise_pct, revenue, net_income
                FROM earnings_history
                WHERE ticker = '{ticker}'
                ORDER BY period_date DESC""",
            conn
        )
        reactions = pd.read_sql(
            f"""SELECT period, period_date, reaction_1d_pct,
                reaction_5d_pct, reaction_30d_pct
                FROM earnings_reactions
                WHERE ticker = '{ticker}'
                ORDER BY period_date DESC""",
            conn
        )
    earnings['period_date'] = earnings['period_date'].astype(str)
    reactions['period_date'] = reactions['period_date'].astype(str)
    return {
        "ticker": ticker,
        "company": COMPANIES[ticker],
        "quarters": len(earnings),
        "earnings_history": earnings.to_dict(orient="records"),
        "price_reactions": reactions.to_dict(orient="records")
    }

@app.get("/stock/{ticker}/prediction")
def stock_prediction(ticker: str):
    ticker = ticker.upper()
    if ticker not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""SELECT * FROM predictions
                WHERE ticker = '{ticker}'
                ORDER BY prediction_date DESC
                LIMIT 1""",
            conn
        )
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No prediction found for {ticker}")
    row = df.iloc[0]
    return {
        "ticker": ticker,
        "company": COMPANIES[ticker],
        "predicted_period": row['predicted_period'],
        "prediction_date": str(row['prediction_date']),
        "predicted_sentiment": row['predicted_sentiment'],
        "sentiment_confidence": round(float(row['sentiment_confidence']) * 100, 1),
        "predicted_reaction_30d": round(float(row['predicted_reaction_30d']), 2),
        "predicted_reaction_1d": round(float(row['predicted_reaction_1d']), 2),
        "model_version": row['model_version'],
        "interpretation": f"Model predicts {row['predicted_sentiment']} sentiment for {row['predicted_period']} with {round(float(row['sentiment_confidence'])*100,1)}% confidence and a {round(float(row['predicted_reaction_30d']),1)}% 30-day price reaction."
    }

@app.get("/correlation")
def correlation():
    with engine.connect() as conn:
        df = pd.read_sql(
            """SELECT ticker, reaction_1d_pct, reaction_5d_pct,
               reaction_30d_pct, eps_surprise_pct
               FROM earnings_reactions
               WHERE eps_surprise_pct IS NOT NULL""",
            conn
        )
    if df.empty:
        raise HTTPException(status_code=404, detail="No reaction data found")

    results = []
    for ticker in df['ticker'].unique():
        t = df[df['ticker'] == ticker]
        if len(t) < 3:
            continue
        corr_1d = round(float(t['eps_surprise_pct'].corr(t['reaction_1d_pct'])), 3)
        corr_30d = round(float(t['eps_surprise_pct'].corr(t['reaction_30d_pct'])), 3)
        avg_reaction = round(float(t['reaction_30d_pct'].mean()), 2)
        results.append({
            "ticker": ticker,
            "company": COMPANIES.get(ticker, ticker),
            "quarters_analyzed": len(t),
            "eps_surprise_vs_1d_correlation": corr_1d,
            "eps_surprise_vs_30d_correlation": corr_30d,
            "avg_30d_reaction": avg_reaction,
        })

    results.sort(key=lambda x: x['eps_surprise_vs_30d_correlation'], reverse=True)
    return {
        "description": "Correlation between EPS surprise % and subsequent price reaction",
        "companies": results
    }