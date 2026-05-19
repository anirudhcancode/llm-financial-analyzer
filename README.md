# LLM Financial Intelligence Platform

An end-to-end financial analytics platform that started as an NLP pipeline to summarize and analyze earnings reports — and evolved into a full intelligence system with historical trend analysis, event detection, and ML-powered predictions across 10 companies.

## What it started as

An NLP pipeline that automatically reads financial earnings call transcripts and produces:
- A plain English summary of the key points
- A sentiment score (positive / negative / neutral) with confidence
- The most important topics and phrases discussed

## What it became

After the core NLP pipeline was working, the natural question was: **does negative earnings sentiment actually predict stock drops?** Answering that required historical data, event detection, and machine learning.

## Results — Original NLP Analysis (5 Companies)

| Ticker | Company | Sentiment | Confidence | Key Finding |
|---|---|---|---|---|
| AAPL | Apple | Negative | 94.88% | China -13%, iPad -25% |
| MSFT | Microsoft | Positive | 95.37% | Azure +28%, AI growth |
| GOOGL | Alphabet | Positive | 74.22% | Cloud profitable, regulatory risks |
| AMZN | Amazon | Positive | 95.98% | AWS reaccelerating |
| NVDA | NVIDIA | Positive | 95.72% | Record revenue +206% YoY |

## Extended Platform — 10 Companies, 5 Phases

### Phase 1 — Historical Stock Data
- 10 years of daily OHLCV price data via yfinance
- 10 companies: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, PLTR, SNOW, DDOG, MDB
- 28,877 total rows stored in PostgreSQL

### Phase 2 — Earnings History
- Up to 49 quarters of earnings data per company
- EPS actual vs estimate, revenue, net income, earnings surprise %
- 454 total earnings records across all 10 companies

### Phase 3 — Event Detection & Analysis
- Detected 1,849 major price events (>5% single-day moves)
- TSLA: 350 events (most volatile) — MSFT: 44 events (most stable)
- Computed 1-day, 5-day, and 30-day price reactions after every earnings release

### Phase 4 — Predictive Model
- GradientBoosting classifier trained on 435 labeled historical samples
- Predicts next-quarter earnings sentiment (positive / negative / neutral)
- Regression model predicts 30-day stock price reaction after earnings
- Features: volatility, momentum, EPS surprise history, revenue growth trends

### Phase 5 — Visualization & API
- 14 interactive Plotly charts generated automatically
- 9 FastAPI endpoints serving historical data, predictions, and correlation analysis
- Live demo page with explanations for non-technical audiences

## Architecture
Raw Text (Transcripts)     →  PostgreSQL  →  BART Summarization
yfinance (Price Data)      →  PostgreSQL  →  FinBERT Sentiment
Earnings Dates (EPS Data)  →  PostgreSQL  →  YAKE Keywords
→  Event Detection
→  GradientBoosting Predictions
→  Plotly Visualizations
→  FastAPI
## Why FinBERT over a general sentiment model?

General models get financial language wrong. "Revenue was flat" sounds neutral but means no growth — negative in finance. "Conservative guidance" sounds cautious but can be strategic. FinBERT was trained specifically on financial text and understands these nuances. It correctly identified Apple as the only negative report — picking up on the China revenue decline that a general model would have missed.

## Tech Stack

| Layer | Technology |
|---|---|
| Data Ingestion | yfinance, manual transcripts |
| Storage | PostgreSQL (Docker) |
| Summarization | facebook/bart-large-cnn (HuggingFace) |
| Sentiment | ProsusAI/finbert (HuggingFace) |
| Keywords | YAKE |
| ML Models | GradientBoosting (scikit-learn) |
| Visualization | Plotly |
| API | FastAPI, Uvicorn |
| Deployment | Render |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | / | Platform info and available endpoints |
| GET | /companies | All 10 tracked companies |
| GET | /reports | All NLP analysis reports |
| GET | /reports/{ticker} | NLP report for a specific company |
| GET | /sentiment/summary | Aggregated sentiment across all reports |
| GET | /stock/{ticker}/history | Price history with metrics |
| GET | /stock/{ticker}/events | Major price events |
| GET | /stock/{ticker}/earnings | Earnings history and price reactions |
| GET | /stock/{ticker}/prediction | Next quarter ML prediction |
| GET | /correlation | EPS surprise vs price reaction correlation |

## Live Demo

- **Original NLP API:** https://llm-financial-analyzer.onrender.com/docs
- **Intelligence Platform:** https://anirudhcancode.github.io/portfolio/llm-intelligence-demo.html
- **Portfolio:** https://anirudhcancode.github.io/portfolio

## Setup

```bash
# Start PostgreSQL
docker compose up -d

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pipelines in order
python src/stock_pipeline.py        # Phase 1 — price data
python src/earnings_pipeline.py     # Phase 2 — earnings history
python src/analysis_pipeline.py     # Phase 3 — event detection
python src/prediction_pipeline.py   # Phase 4 — ML predictions
python src/visualizations.py        # Phase 5 — charts

# Start API
uvicorn api.main:app --reload
```

## Dataset

- Stock prices: 10 years daily OHLCV via yfinance (2015–2026)
- Earnings: Up to 49 quarters per company via yfinance earnings dates
- NLP transcripts: Real earnings call transcripts (Q3/Q4 2023 — Q1/Q2 2024)
- Companies: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, PLTR, SNOW, DDOG, MDB