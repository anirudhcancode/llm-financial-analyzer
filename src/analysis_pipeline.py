import os
import pandas as pd
import numpy as np
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
            CREATE TABLE IF NOT EXISTS market_events (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                date DATE,
                event_type VARCHAR(50),
                price_change_pct FLOAT,
                close_price FLOAT,
                volume BIGINT,
                description TEXT,
                UNIQUE(ticker, date, event_type)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS price_metrics (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                date DATE,
                close FLOAT,
                daily_return FLOAT,
                volatility_30d FLOAT,
                momentum_30d FLOAT,
                momentum_90d FLOAT,
                avg_volume_30d FLOAT,
                UNIQUE(ticker, date)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS earnings_reactions (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                period VARCHAR(20),
                period_date DATE,
                price_1d_after FLOAT,
                price_5d_after FLOAT,
                price_30d_after FLOAT,
                reaction_1d_pct FLOAT,
                reaction_5d_pct FLOAT,
                reaction_30d_pct FLOAT,
                eps_surprise_pct FLOAT,
                UNIQUE(ticker, period_date)
            );
        """))
        conn.commit()
    print("Analysis tables created")

def load_prices(ticker: str) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            f"SELECT * FROM stock_prices WHERE ticker = '{ticker}' ORDER BY date",
            conn
        )
    df['date'] = pd.to_datetime(df['date'])
    return df

def compute_price_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values('date').reset_index(drop=True)
    df['daily_return'] = df['close'].pct_change() * 100
    df['volatility_30d'] = df['daily_return'].rolling(30).std()
    df['momentum_30d'] = df['close'].pct_change(30) * 100
    df['momentum_90d'] = df['close'].pct_change(90) * 100
    df['avg_volume_30d'] = df['volume'].rolling(30).mean()
    return df

def detect_major_events(df: pd.DataFrame, ticker: str, threshold: float = 5.0) -> pd.DataFrame:
    df = df.copy()
    df['daily_return'] = df['close'].pct_change() * 100
    events = df[abs(df['daily_return']) >= threshold].copy()

    records = []
    for _, row in events.iterrows():
        direction = "surge" if row['daily_return'] > 0 else "drop"
        records.append({
            "ticker": ticker,
            "date": row['date'].date(),
            "event_type": f"major_{direction}",
            "price_change_pct": round(row['daily_return'], 2),
            "close_price": round(row['close'], 2),
            "volume": int(row['volume']),
            "description": f"{ticker} {direction}d {abs(row['daily_return']):.1f}% on {row['date'].strftime('%Y-%m-%d')}"
        })

    return pd.DataFrame(records)

def compute_earnings_reactions(ticker: str, prices_df: pd.DataFrame) -> pd.DataFrame:
    with engine.connect() as conn:
        earnings = pd.read_sql(
            f"SELECT * FROM earnings_history WHERE ticker = '{ticker}' ORDER BY period_date",
            conn
        )

    if earnings.empty:
        return pd.DataFrame()

    prices_df = prices_df.copy()
    prices_df['date'] = pd.to_datetime(prices_df['date'])
    prices_df = prices_df.set_index('date').sort_index()

    records = []
    for _, row in earnings.iterrows():
        try:
            period_date = pd.to_datetime(row['period_date'])

            # Find nearest trading day
            available_dates = prices_df.index
            nearest = min(available_dates, key=lambda x: abs((x - period_date).days))
            base_price = prices_df.loc[nearest, 'close']

            # Price 1, 5, 30 days after
            def get_price_after(days):
                target = nearest + pd.Timedelta(days=days)
                future = available_dates[available_dates >= target]
                if len(future) == 0:
                    return None
                return prices_df.loc[future[0], 'close']

            p1 = get_price_after(1)
            p5 = get_price_after(5)
            p30 = get_price_after(30)

            records.append({
                "ticker": ticker,
                "period": row['period'],
                "period_date": row['period_date'],
                "price_1d_after": round(p1, 2) if p1 else None,
                "price_5d_after": round(p5, 2) if p5 else None,
                "price_30d_after": round(p30, 2) if p30 else None,
                "reaction_1d_pct": round((p1 - base_price) / base_price * 100, 2) if p1 else None,
                "reaction_5d_pct": round((p5 - base_price) / base_price * 100, 2) if p5 else None,
                "reaction_30d_pct": round((p30 - base_price) / base_price * 100, 2) if p30 else None,
                "eps_surprise_pct": row.get('eps_surprise_pct', None)
            })
        except Exception as e:
            continue

    return pd.DataFrame(records)

def save_price_metrics(df: pd.DataFrame, ticker: str, engine):
    df = df[['date', 'close', 'daily_return', 'volatility_30d',
             'momentum_30d', 'momentum_90d', 'avg_volume_30d']].copy()
    df['ticker'] = ticker
    df['date'] = df['date'].dt.date
    df = df.dropna(subset=['daily_return'])

    with engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO price_metrics
                    (ticker, date, close, daily_return, volatility_30d,
                     momentum_30d, momentum_90d, avg_volume_30d)
                    VALUES (:ticker, :date, :close, :daily_return, :volatility_30d,
                            :momentum_30d, :momentum_90d, :avg_volume_30d)
                    ON CONFLICT (ticker, date) DO NOTHING
                """), row.to_dict())
            except:
                continue
        conn.commit()
    print(f"  Saved {len(df)} price metric rows for {ticker}")

def save_events(df: pd.DataFrame, engine):
    if df.empty:
        return
    with engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO market_events
                    (ticker, date, event_type, price_change_pct, close_price, volume, description)
                    VALUES (:ticker, :date, :event_type, :price_change_pct,
                            :close_price, :volume, :description)
                    ON CONFLICT (ticker, date, event_type) DO NOTHING
                """), row.to_dict())
            except:
                continue
        conn.commit()
    print(f"  Saved {len(df)} events for {df['ticker'].iloc[0]}")

def save_earnings_reactions(df: pd.DataFrame, engine):
    if df.empty:
        return
    with engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO earnings_reactions
                    (ticker, period, period_date, price_1d_after, price_5d_after,
                     price_30d_after, reaction_1d_pct, reaction_5d_pct,
                     reaction_30d_pct, eps_surprise_pct)
                    VALUES (:ticker, :period, :period_date, :price_1d_after,
                            :price_5d_after, :price_30d_after, :reaction_1d_pct,
                            :reaction_5d_pct, :reaction_30d_pct, :eps_surprise_pct)
                    ON CONFLICT (ticker, period_date) DO NOTHING
                """), row.to_dict())
            except:
                continue
        conn.commit()
    print(f"  Saved {len(df)} earnings reactions for {df['ticker'].iloc[0]}")

if __name__ == "__main__":
    print("Starting analysis pipeline...")
    create_tables(engine)

    for ticker, company in COMPANIES.items():
        print(f"\nProcessing {ticker} — {company}")

        prices = load_prices(ticker)
        if prices.empty:
            print(f"  No price data for {ticker}")
            continue

        # Compute price metrics
        metrics = compute_price_metrics(prices)
        save_price_metrics(metrics, ticker, engine)

        # Detect major price events
        events = detect_major_events(prices, ticker, threshold=5.0)
        print(f"  Found {len(events)} major price events")
        save_events(events, engine)

        # Compute earnings reactions
        reactions = compute_earnings_reactions(ticker, prices)
        if not reactions.empty:
            save_earnings_reactions(reactions, engine)
            print(f"  Earnings reactions computed")

    print("\nAnalysis pipeline complete!")