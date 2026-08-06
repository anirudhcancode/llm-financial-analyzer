# LLM Financial Intelligence Platform

An end-to-end financial analytics platform that started as an NLP pipeline to summarize and analyze earnings reports — and evolved into a full intelligence system with historical trend analysis, event detection, and ML-powered predictions across 10 companies.

## The Problem

Every quarter, every public company publishes an earnings report. Analysts and investors need to read hundreds of these — each one can be 50+ pages or an hour-long call transcript. The system started by automating that. Then grew to answer a deeper question: **does earnings sentiment actually predict stock price movement?**

## Live Demos

- **Original NLP API:** https://llm-financial-analyzer.onrender.com/docs
- **Intelligence Platform:** https://anirudhcancode.github.io/portfolio/llm-intelligence-demo.html
- **Demo Page:** https://anirudhcancode.github.io/portfolio/llm-demo.html

## Part 1 — The NLP Pipeline

### Three Models

**BART — Summarization**
- Built by Facebook, trained on news articles and books
- Abstractive summarizer — rewrites content in its own words, not just extracting sentences
- Condenses 10,000+ word earnings transcripts into plain English summaries in seconds

**FinBERT — Sentiment Analysis**
- BERT fine-tuned specifically on financial text — SEC filings, earnings calls, analyst reports
- Why not a general model: financial language is different. "Revenue was flat" sounds neutral but means no growth — negative in finance. FinBERT understands these nuances.
- Correctly identified Apple as the only negative report at 94.88% confidence

**YAKE — Keyword Extraction**
- Statistical algorithm — no GPU, no training, no model needed
- Scores words on frequency, position, context, and co-occurrence
- Fast and domain-agnostic

### NLP Results — 5 Companies

| Ticker | Company | Sentiment | Confidence | Key Finding |
|---|---|---|---|---|
| AAPL | Apple | **Negative** | 94.88% | China -13%, iPad -25% |
| MSFT | Microsoft | Positive | 95.37% | Azure +28%, AI growth |
| GOOGL | Alphabet | Positive | 74.22% | Cloud profitable, regulatory risks |
| AMZN | Amazon | Positive | 95.98% | AWS reaccelerating |
| NVDA | NVIDIA | Positive | 95.72% | Record revenue +206% YoY |

## Part 2 — The Intelligence Platform

After the NLP pipeline, the question was: does negative sentiment predict stock drops? Answering that required historical data, event detection, and machine learning.

### Platform Numbers

| Metric | Value |
|---|---|
| Companies | 10 |
| Stock price records | 28,877 |
| Earnings records | 454 (up to 40 quarters per company) |
| Major market events detected | 1,849 |
| ML training samples | 435 |
| Interactive charts | 14 |

### Phase 1 — Historical Stock Data
- 10 years of daily OHLCV price data via yfinance
- 10 companies: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, PLTR, SNOW, DDOG, MDB
- 28,877 total rows stored in PostgreSQL

### Phase 2 — Earnings History
- Up to 40 quarters of earnings data per company via yfinance earnings dates
- EPS actual vs estimate, revenue, net income, earnings surprise %
- 454 total earnings records — large caps go back to 2014

### Phase 3 — Event Detection & Analysis
- Detected 1,849 major price events (>5% single-day moves)
- TSLA: 350 events (most volatile) — MSFT: 44 events (most stable)
- Computed 1-day, 5-day, and 30-day price reactions after every earnings release

### Phase 4 — Predictive Model
- GradientBoosting classifier: predicts next quarter earnings sentiment
- GradientBoosting regressor: predicts 30-day post-earnings price reaction
- Features: volatility, momentum, EPS surprise history, revenue growth trends
- Why GradientBoosting not neural network: only 435 samples — tree-based methods outperform neural networks on small tabular datasets

### Phase 5 — Visualization & API
- 14 interactive Plotly charts: normalized performance, price history with event markers, earnings reaction heatmap, volatility comparison, predictions
- 9 FastAPI endpoints serving historical data, predictions, and correlation analysis

## Architecture
Earnings Transcripts  →  PostgreSQL  →  BART Summarization
→  FinBERT Sentiment
→  YAKE Keywords
yfinance Price Data   →  PostgreSQL  →  Price Metrics
yfinance EPS Data     →  PostgreSQL  →  Earnings History
→  Event Detection (1,849 events)
→  Earnings Reactions
→  GradientBoosting Predictions
→  Plotly Visualizations (14 charts)
→  FastAPI (9 endpoints)
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
- Earnings: Up to 40 quarters per company via yfinance earnings dates
- NLP transcripts: Real earnings call transcripts (Q3/Q4 2023 — Q1/Q2 2024)
- Companies: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, PLTR, SNOW, DDOG, MDB

## Portfolio

https://anirudhcancode.github.io/portfolio