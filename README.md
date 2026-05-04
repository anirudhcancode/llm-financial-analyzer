# LLM Financial Report Analyzer

An NLP pipeline that automatically summarizes financial earnings reports, analyzes sentiment using domain-specific language models, and extracts key topics — serving all results via a REST API.

## What it does

Instead of an analyst spending hours reading a 50-page earnings report, this system processes it in seconds and returns:
- A plain English summary of the key points
- A sentiment score (positive / negative / neutral) with confidence
- The most important topics and phrases discussed

## Results — 5 Major Companies Analyzed

| Ticker | Company | Sentiment | Confidence | Key Finding |
|---|---|---|---|---|
| AAPL | Apple | Negative | 94.88% | China -13%, iPad -25% |
| MSFT | Microsoft | Positive | 95.37% | Azure +28%, AI growth |
| GOOGL | Alphabet | Positive | 74.22% | Cloud profitable, regulatory risks |
| AMZN | Amazon | Positive | 95.98% | AWS reaccelerating |
| NVDA | NVIDIA | Positive | 95.72% | Record revenue +206% YoY |

## Architecture

Raw Text → PostgreSQL → BART Summarization → FinBERT Sentiment → YAKE Keywords → FastAPI

## Tech Stack

- **Summarization:** facebook/bart-large-cnn (HuggingFace Transformers)
- **Sentiment:** ProsusAI/finbert — BERT fine-tuned on financial text
- **Keywords:** YAKE — statistical keyword extraction, no GPU required
- **Database:** PostgreSQL (Docker)
- **API:** FastAPI, Uvicorn
- **Data:** pandas, SQLAlchemy

## Why FinBERT instead of a general sentiment model?

General models get financial language wrong. "Revenue was flat" sounds neutral but means no growth — negative in finance. "Conservative guidance" sounds cautious but is often strategic. FinBERT was trained specifically on financial text and understands these nuances. It correctly identified Apple as the only negative report — picking up on China revenue declines that a general model would have missed.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | / | Health check |
| POST | /analyze | Analyze a new financial report |
| GET | /reports | Retrieve all stored analyses |
| GET | /reports/{ticker} | Get analysis for a specific company |
| GET | /sentiment/summary | Aggregated sentiment across all reports |

## Live Demo

https://llm-financial-analyzer.onrender.com/docs

## Setup

```bash
# Run PostgreSQL
docker compose up -d

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ingest reports and run analysis
python src/ingest.py
python src/analyze.py

# Start API
uvicorn api.main:app --reload
```

## Dataset

5 real earnings call transcripts: AAPL, MSFT, GOOGL, AMZN, NVDA (Q3/Q4 2023 — Q1/Q2 2024)