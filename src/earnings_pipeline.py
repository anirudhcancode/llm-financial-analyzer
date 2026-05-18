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

def get_row_value(income, row_names, col):
    for name in row_names:
        for idx in income.index:
            if str(idx).lower().strip() == name.lower().strip():
                val = income.loc[idx, col]
                if pd.isna(val):
                    return None
                try:
                    return int(val)
                except (ValueError, OverflowError):
                    return None
    return None

def fetch_earnings(ticker: str) -> pd.DataFrame:
    print(f"  Fetching earnings for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        records = []

        # Get up to 40 quarters of earnings dates with EPS data
        try:
            earnings_dates = stock.get_earnings_dates(limit=40)
        except:
            earnings_dates = stock.earnings_dates

        if earnings_dates is None or earnings_dates.empty:
            print(f"  No earnings dates for {ticker}")
            return pd.DataFrame()

        # Get income statement for recent quarters
        try:
            income = stock.quarterly_income_stmt
        except:
            income = None

        for idx, row in earnings_dates.iterrows():
            try:
                date = pd.to_datetime(idx).date()
                year = date.year
                quarter = (date.month - 1) // 3 + 1
                period = f"Q{quarter} {year}"

                eps_actual = row.get("Reported EPS", None)
                eps_estimate = row.get("EPS Estimate", None)
                surprise_pct = row.get("Surprise(%)", None)

                # Clean up NaN values
                eps_actual = float(eps_actual) if eps_actual is not None and not pd.isna(eps_actual) else None
                eps_estimate = float(eps_estimate) if eps_estimate is not None and not pd.isna(eps_estimate) else None
                surprise_pct = float(surprise_pct) if surprise_pct is not None and not pd.isna(surprise_pct) else None

                # Try to get revenue from income statement
                revenue = None
                net_income = None
                gross_profit = None
                operating_income = None

                if income is not None and not income.empty:
                    for col in income.columns:
                        col_date = pd.to_datetime(col).date()
                        if abs((col_date - date).days) < 45:
                            revenue = get_row_value(income, ['total revenue', 'operating revenue'], col)
                            net_income = get_row_value(income, ['net income', 'net income common stockholders'], col)
                            gross_profit = get_row_value(income, ['gross profit'], col)
                            operating_income = get_row_value(income, ['operating income', 'ebit'], col)
                            break

                records.append({
                    "ticker": ticker,
                    "period": period,
                    "period_date": date,
                    "revenue": revenue,
                    "revenue_estimate": None,
                    "revenue_surprise_pct": None,
                    "eps_actual": eps_actual,
                    "eps_estimate": eps_estimate,
                    "eps_surprise_pct": surprise_pct,
                    "net_income": net_income,
                    "gross_profit": gross_profit,
                    "operating_income": operating_income,
                })
            except Exception as e:
                continue

        df = pd.DataFrame(records)
        # Remove future dates
        df = df[pd.to_datetime(df['period_date']) <= pd.Timestamp.today()]
        print(f"  Found {len(df)} quarters for {ticker}")
        return df

    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        return pd.DataFrame()

def save_earnings(df: pd.DataFrame, engine):
    if df.empty:
        return
    saved = 0
    for _, row in df.iterrows():
        row_dict = {}
        for k, v in row.to_dict().items():
            if isinstance(v, float) and pd.isna(v):
                row_dict[k] = None
            else:
                row_dict[k] = v
        try:
            with engine.connect() as conn:
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
                        eps_surprise_pct = EXCLUDED.eps_surprise_pct,
                        net_income = EXCLUDED.net_income,
                        gross_profit = EXCLUDED.gross_profit,
                        operating_income = EXCLUDED.operating_income
                """), row_dict)
                conn.commit()
                saved += 1
        except Exception as e:
            continue
    print(f"  Saved {saved} earnings records for {df['ticker'].iloc[0]}")

if __name__ == "__main__":
    print("Starting earnings history pipeline...")
    create_tables(engine)

    for ticker, company in COMPANIES.items():
        print(f"\nProcessing {ticker} — {company}")
        df = fetch_earnings(ticker)
        save_earnings(df, engine)

    print("\nEarnings pipeline complete!")