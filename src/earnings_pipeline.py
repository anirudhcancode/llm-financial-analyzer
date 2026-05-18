import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings("ignore")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

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

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS earnings_history (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                period VARCHAR(20),
                period_date DATE,
                revenue BIGINT,
                revenue_estimate BIGINT,
                revenue_surprise_pct FLOAT,
                eps_actual FLOAT,
                eps_estimate FLOAT,
                eps_surprise_pct FLOAT,
                net_income BIGINT,
                gross_profit BIGINT,
                operating_income BIGINT,
                UNIQUE(ticker, period_date)
            );
        """))
        conn.commit()
    print("Earnings history table created")

def fetch_earnings(ticker: str) -> pd.DataFrame:
    print(f"  Fetching earnings for {ticker}...")
    try:
        stock = yf.Ticker(ticker)

        # Get income statement (quarterly)
        income = stock.quarterly_income_stmt
        if income is None or income.empty:
            print(f"  No income statement for {ticker}")
            return pd.DataFrame()

        records = []
        for col in income.columns:
            try:
                period_date = pd.to_datetime(col).date()
                year = period_date.year
                quarter = (period_date.month - 1) // 3 + 1
                period = f"Q{quarter} {year}"

                revenue = None
                net_income = None
                gross_profit = None
                operating_income = None

                for idx in income.index:
                    idx_lower = str(idx).lower()
                    val = income.loc[idx, col]
                    if pd.isna(val):
                        val = None
                    else:
                        val = int(val)

                    if 'total revenue' in idx_lower or 'revenue' in idx_lower:
                        if revenue is None:
                            revenue = val
                    elif 'net income' in idx_lower:
                        if net_income is None:
                            net_income = val
                    elif 'gross profit' in idx_lower:
                        gross_profit = val
                    elif 'operating income' in idx_lower or 'ebit' in idx_lower:
                        if operating_income is None:
                            operating_income = val

                records.append({
                    "ticker": ticker,
                    "period": period,
                    "period_date": period_date,
                    "revenue": revenue,
                    "revenue_estimate": None,
                    "revenue_surprise_pct": None,
                    "eps_actual": None,
                    "eps_estimate": None,
                    "eps_surprise_pct": None,
                    "net_income": net_income,
                    "gross_profit": gross_profit,
                    "operating_income": operating_income,
                })
            except Exception as e:
                continue

        # Get EPS data
        try:
            earnings_dates = stock.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                for idx, row in earnings_dates.iterrows():
                    date = pd.to_datetime(idx).date()
                    eps_actual = row.get("Reported EPS", None)
                    eps_estimate = row.get("EPS Estimate", None)
                    surprise_pct = row.get("Surprise(%)", None)

                    for record in records:
                        diff = abs((pd.to_datetime(record["period_date"]) -
                                    pd.to_datetime(date)).days)
                        if diff < 45:
                            if eps_actual and not pd.isna(eps_actual):
                                record["eps_actual"] = float(eps_actual)
                            if eps_estimate and not pd.isna(eps_estimate):
                                record["eps_estimate"] = float(eps_estimate)
                            if surprise_pct and not pd.isna(surprise_pct):
                                record["eps_surprise_pct"] = float(surprise_pct)
                            break
        except Exception as e:
            pass

        df = pd.DataFrame(records)
        print(f"  Found {len(df)} quarters for {ticker}")
        return df

    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return pd.DataFrame()

def save_earnings(df: pd.DataFrame, engine):
    if df.empty:
        return
    with engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO earnings_history
                    (ticker, period, period_date, revenue, revenue_estimate,
                     revenue_surprise_pct, eps_actual, eps_estimate,
                     eps_surprise_pct, net_income, gross_profit, operating_income)
                    VALUES
                    (:ticker, :period, :period_date, :revenue, :revenue_estimate,
                     :revenue_surprise_pct, :eps_actual, :eps_estimate,
                     :eps_surprise_pct, :net_income, :gross_profit, :operating_income)
                    ON CONFLICT (ticker, period_date) DO UPDATE SET
                        revenue = EXCLUDED.revenue,
                        eps_actual = EXCLUDED.eps_actual,
                        eps_surprise_pct = EXCLUDED.eps_surprise_pct
                """), row.to_dict())
            except Exception as e:
                continue
        conn.commit()
    print(f"  Saved {len(df)} earnings records for {df['ticker'].iloc[0]}")

if __name__ == "__main__":
    print("Starting earnings history pipeline...")
    create_tables(engine)

    for ticker, company in COMPANIES.items():
        print(f"\nProcessing {ticker} — {company}")
        df = fetch_earnings(ticker)
        save_earnings(df, engine)

    print("\nEarnings pipeline complete!")