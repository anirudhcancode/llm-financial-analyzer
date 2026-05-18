import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

# 10 companies — large, mid, small
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

START_DATE = "2015-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                date DATE,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                volume BIGINT,
                adj_close FLOAT,
                UNIQUE(ticker, date)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_info (
                ticker VARCHAR(10) PRIMARY KEY,
                company VARCHAR(100),
                sector VARCHAR(100),
                industry VARCHAR(100),
                market_cap BIGINT,
                country VARCHAR(50)
            );
        """))
        conn.commit()
    print("Tables created successfully")

def fetch_stock_prices(ticker: str, start: str, end: str) -> pd.DataFrame:
    print(f"  Fetching price data for {ticker}...")
    stock = yf.Ticker(ticker)
    df = stock.history(start=start, end=end, auto_adjust=True)
    if df.empty:
        print(f"  No data found for {ticker}")
        return pd.DataFrame()
    df = df.reset_index()
    df["ticker"] = ticker
    df["date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })
    df["adj_close"] = df["close"]
    df = df[["ticker", "date", "open", "high", "low", "close", "volume", "adj_close"]]
    return df

def fetch_company_info(ticker: str, company_name: str) -> dict:
    print(f"  Fetching company info for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker,
            "company": company_name,
            "sector": info.get("sector", "Technology"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "country": info.get("country", "United States")
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "company": company_name,
            "sector": "Technology",
            "industry": "Unknown",
            "market_cap": 0,
            "country": "United States"
        }

def save_stock_prices(df: pd.DataFrame, engine):
    if df.empty:
        return
    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO stock_prices (ticker, date, open, high, low, close, volume, adj_close)
                VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :adj_close)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    adj_close = EXCLUDED.adj_close
            """), row.to_dict())
        conn.commit()
    print(f"  Saved {len(df)} rows for {df['ticker'].iloc[0]}")

def save_company_info(info: dict, engine):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO company_info (ticker, company, sector, industry, market_cap, country)
            VALUES (:ticker, :company, :sector, :industry, :market_cap, :country)
            ON CONFLICT (ticker) DO UPDATE SET
                market_cap = EXCLUDED.market_cap,
                sector = EXCLUDED.sector
        """), info)
        conn.commit()

if __name__ == "__main__":
    print("Starting stock data pipeline...")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Companies: {len(COMPANIES)}\n")

    create_tables(engine)

    for ticker, company in COMPANIES.items():
        print(f"\nProcessing {ticker} — {company}")
        
        # Fetch and save price data
        df = fetch_stock_prices(ticker, START_DATE, END_DATE)
        save_stock_prices(df, engine)
        
        # Fetch and save company info
        info = fetch_company_info(ticker, company)
        save_company_info(info, engine)

    print("\nStock pipeline complete!")
    print(f"Processed {len(COMPANIES)} companies")