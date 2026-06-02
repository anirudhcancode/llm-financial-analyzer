import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="LLM Financial Intelligence Platform",
    description="NLP sentiment analysis of financial earnings reports using BART, FinBERT, and YAKE",
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

# ── Pre-computed NLP results — no database required ──
REPORTS = [
    {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "period": "Q2 2024",
        "sentiment_label": "negative",
        "sentiment_score": 0.9488,
        "summary": "Apple reported Q2 2024 revenue of $90.8 billion, down 4% year over year. China revenue declined 13% to $16.4 billion driven by increased competition. iPad revenue fell 25%. Services revenue grew 14% to a record $23.9 billion. The company announced a record $110 billion share buyback program.",
        "keywords": "China revenue, services revenue, share buyback, iPad revenue, iPhone sales, emerging markets, competition"
    },
    {
        "ticker": "MSFT",
        "company": "Microsoft Corporation",
        "period": "Q3 2024",
        "sentiment_label": "positive",
        "sentiment_score": 0.9537,
        "summary": "Microsoft reported Q3 2024 revenue of $61.9 billion, up 17% year over year. Azure cloud revenue grew 28%, driven by strong AI demand. Copilot integrations are accelerating enterprise adoption. Operating income grew 23% with expanding margins across all segments.",
        "keywords": "Azure growth, AI demand, Copilot, cloud revenue, enterprise adoption, operating margin, intelligent cloud"
    },
    {
        "ticker": "GOOGL",
        "company": "Alphabet Inc.",
        "period": "Q1 2024",
        "sentiment_label": "positive",
        "sentiment_score": 0.7422,
        "summary": "Alphabet reported Q1 2024 revenue of $80.5 billion, up 15%. Google Cloud reached profitability with $900 million operating income. Search revenue grew 14% driven by AI-enhanced results. The company faces ongoing regulatory scrutiny in the EU and US antitrust proceedings.",
        "keywords": "Google Cloud, profitability, Search revenue, regulatory risk, AI integration, YouTube, antitrust"
    },
    {
        "ticker": "AMZN",
        "company": "Amazon.com Inc.",
        "period": "Q1 2024",
        "sentiment_label": "positive",
        "sentiment_score": 0.9598,
        "summary": "Amazon reported Q1 2024 revenue of $143.3 billion, up 13%. AWS revenue grew 17% to $25 billion as cloud demand reaccelerates. Operating income surged to $15.3 billion from $4.8 billion a year ago. Advertising revenue grew 24%. The company raised Q2 guidance above expectations.",
        "keywords": "AWS reacceleration, operating income, advertising revenue, cloud demand, margins, guidance, Prime"
    },
    {
        "ticker": "NVDA",
        "company": "NVIDIA Corporation",
        "period": "Q1 2025",
        "sentiment_label": "positive",
        "sentiment_score": 0.9572,
        "summary": "NVIDIA reported Q1 2025 revenue of $26 billion, up 206% year over year and above all estimates. Data center revenue reached $22.6 billion driven by insatiable AI infrastructure demand. Blackwell GPU architecture is ramping ahead of schedule. Operating margin expanded to 65%.",
        "keywords": "data center revenue, Blackwell architecture, AI infrastructure, record revenue, operating margin, GPU demand, H100"
    }
]

@app.get("/")
def root():
    return {
        "name": "LLM Financial Intelligence Platform",
        "version": "2.0.0",
        "description": "NLP pipeline using BART (summarization), FinBERT (sentiment), and YAKE (keywords) to analyze financial earnings reports",
        "nlp_companies": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        "platform_companies": list(COMPANIES.keys()),
        "endpoints": [
            "/reports",
            "/reports/{ticker}",
            "/sentiment/summary",
            "/companies"
        ],
        "demo": "https://anirudhcancode.github.io/portfolio/llm-demo.html",
        "intelligence_platform": "https://anirudhcancode.github.io/portfolio/llm-intelligence-demo.html"
    }

@app.get("/companies")
def get_companies():
    return {
        "nlp_analyzed": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        "platform_tracked": COMPANIES
    }

@app.get("/reports")
def get_reports():
    return {
        "count": len(REPORTS),
        "models_used": {
            "summarization": "facebook/bart-large-cnn",
            "sentiment": "ProsusAI/finbert",
            "keywords": "YAKE"
        },
        "reports": REPORTS
    }

@app.get("/reports/{ticker}")
def get_report(ticker: str):
    ticker = ticker.upper()
    for report in REPORTS:
        if report["ticker"] == ticker:
            return report
    raise HTTPException(
        status_code=404,
        detail=f"No NLP report found for {ticker}. Analyzed companies: AAPL, MSFT, GOOGL, AMZN, NVDA"
    )

@app.get("/sentiment/summary")
def sentiment_summary():
    positive = [r for r in REPORTS if r["sentiment_label"] == "positive"]
    negative = [r for r in REPORTS if r["sentiment_label"] == "negative"]
    neutral = [r for r in REPORTS if r["sentiment_label"] == "neutral"]

    most_positive = max(REPORTS, key=lambda x: x["sentiment_score"] if x["sentiment_label"] == "positive" else 0)
    most_negative = min(REPORTS, key=lambda x: x["sentiment_score"] if x["sentiment_label"] == "negative" else 1)

    return {
        "total_reports": len(REPORTS),
        "positive": len(positive),
        "negative": len(negative),
        "neutral": len(neutral),
        "most_positive": most_positive["ticker"],
        "most_negative": most_negative["ticker"],
        "key_finding": "Apple (AAPL) was the only negative report at 94.88% confidence — driven by 13% China revenue decline and 25% iPad revenue drop",
        "reports": [
            {
                "ticker": r["ticker"],
                "company": r["company"],
                "sentiment_label": r["sentiment_label"],
                "sentiment_score": r["sentiment_score"],
                "period": r["period"]
            }
            for r in REPORTS
        ]
    }

@app.get("/analyze")
def analyze_info():
    return {
        "message": "On-demand analysis requires GPU inference which is not available on the free deployment tier.",
        "pre_computed_results": "Use GET /reports or GET /reports/{ticker} to access pre-computed results for AAPL, MSFT, GOOGL, AMZN, NVDA",
        "models": {
            "summarization": "facebook/bart-large-cnn — abstractive summarization",
            "sentiment": "ProsusAI/finbert — BERT fine-tuned on financial text",
            "keywords": "YAKE — statistical keyword extraction"
        },
        "intelligence_platform": "https://anirudhcancode.github.io/portfolio/llm-intelligence-demo.html"
    }