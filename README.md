# LLM Financial Report Analyzer

An NLP pipeline that automatically summarizes financial reports, analyzes sentiment, and extracts key insights using open source language models.

## What it does

- Ingests earnings call transcripts and financial reports into PostgreSQL
- Summarizes long reports using BART (facebook/bart-large-cnn)
- Analyzes financial sentiment using FinBERT (ProsusAI/finbert) — a model specifically trained on financial text
- Extracts key phrases using YAKE keyword extraction
- Exposes all results via a FastAPI REST API

## Architecture

Raw Text → PostgreSQL → BART Summarization → FinBERT Sentiment → YAKE Keywords → FastAPI

## Tech Stack

- NLP Models: facebook/bart-large-cnn, ProsusAI/finbert (HuggingFace Transformers)
- Database: PostgreSQL (Docker)
- API: FastAPI, Uvicorn
- Data: pandas, SQLAlchemy
- Keyword Extraction: YAKE

## API Endpoints

GET  /                    — Health check
POST /analyze             — Analyze a new financial report
GET  /reports             — Retrieve all stored analyses
GET  /reports/{ticker}    — Get analysis for a specific company
GET  /sentiment/summary   — Sentiment breakdown across all reports

## Sample Results

Ticker | Sentiment | Confidence | Key Finding
AAPL   | Negative  | 94.88%     | China revenue down 13%, iPad down 25%
MSFT   | Positive  | 95.37%     | Azure up 28%, AI driving growth
GOOGL  | Positive  | 74.22%     | Cloud turned profitable, regulatory risks
AMZN   | Positive  | 95.98%     | AWS reaccelerating, margins improving
NVDA   | Positive  | 95.72%     | Record revenue, 206% YoY growth

## Setup

Prerequisites: Python 3.10+, Docker Desktop

Run PostgreSQL:
docker compose up -d

Install dependencies:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Ingest sample reports:
python src/ingest.py

Run NLP analysis:
python src/analyze.py

Start the API:
uvicorn api.main:app --reload

Test endpoints:
curl http://127.0.0.1:8000/reports
curl http://127.0.0.1:8000/sentiment/summary

## Dataset

5 real earnings call transcripts: AAPL, MSFT, GOOGL, AMZN, NVDA (Q3/Q4 2023 — Q1/Q2 2024)