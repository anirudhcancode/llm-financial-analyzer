import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from collections import Counter
import joblib
import warnings
warnings.filterwarnings("ignore")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

COMPANIES = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "PLTR", "SNOW", "DDOG", "MDB"
]

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                predicted_period VARCHAR(20),
                prediction_date DATE,
                predicted_sentiment VARCHAR(20),
                sentiment_confidence FLOAT,
                predicted_reaction_1d FLOAT,
                predicted_reaction_30d FLOAT,
                features_used TEXT,
                model_version VARCHAR(20),
                UNIQUE(ticker, predicted_period)
            );
        """))
        conn.commit()
    print("Predictions table created")

def build_features(ticker: str) -> pd.DataFrame:
    with engine.connect() as conn:
        prices = pd.read_sql(
            f"""SELECT date, close, daily_return, volatility_30d,
                momentum_30d, momentum_90d, avg_volume_30d
                FROM price_metrics WHERE ticker = '{ticker}'
                ORDER BY date""",
            conn
        )

        earnings = pd.read_sql(
            f"""SELECT period_date, eps_actual, eps_estimate,
                eps_surprise_pct, revenue, net_income, operating_income
                FROM earnings_history WHERE ticker = '{ticker}'
                ORDER BY period_date""",
            conn
        )

        reactions = pd.read_sql(
            f"""SELECT period_date, reaction_1d_pct, reaction_5d_pct,
                reaction_30d_pct, eps_surprise_pct
                FROM earnings_reactions WHERE ticker = '{ticker}'
                ORDER BY period_date""",
            conn
        )

    if earnings.empty or prices.empty:
        return pd.DataFrame()

    prices['date'] = pd.to_datetime(prices['date'])
    earnings['period_date'] = pd.to_datetime(earnings['period_date'])

    records = []
    for i, row in earnings.iterrows():
        period_date = row['period_date']

        window_start = period_date - pd.Timedelta(days=30)
        window_prices = prices[
            (prices['date'] >= window_start) &
            (prices['date'] <= period_date)
        ]

        if window_prices.empty:
            continue

        # Revenue growth
        if i > 0:
            prev_revenue = earnings.iloc[i-1]['revenue']
            curr_revenue = row['revenue']
            if prev_revenue and curr_revenue and prev_revenue != 0:
                revenue_growth = (curr_revenue - prev_revenue) / abs(prev_revenue) * 100
            else:
                revenue_growth = 0
        else:
            revenue_growth = 0

        # Get reaction for this period
        if not reactions.empty:
            reactions['period_date'] = pd.to_datetime(reactions['period_date'])
            diffs = (reactions['period_date'] - period_date).abs().dt.days
            reaction_row = reactions[diffs < 60]
        else:
            reaction_row = pd.DataFrame()

        reaction_1d = float(reaction_row['reaction_1d_pct'].values[0]) if not reaction_row.empty else 0
        reaction_30d = float(reaction_row['reaction_30d_pct'].values[0]) if not reaction_row.empty else 0
        eps_surprise = float(row.get('eps_surprise_pct', 0) or 0)

        # Price-based sentiment proxy
        if reaction_30d > 3 or eps_surprise > 5:
            sentiment_label = "positive"
        elif reaction_30d < -3 or eps_surprise < -5:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        features = {
            "ticker": ticker,
            "period_date": period_date,
            "volatility_30d": float(window_prices['volatility_30d'].mean() or 0),
            "momentum_30d": float(window_prices['momentum_30d'].mean() or 0),
            "momentum_90d": float(window_prices['momentum_90d'].mean() or 0),
            "avg_daily_return": float(window_prices['daily_return'].mean() or 0),
            "eps_surprise_pct": eps_surprise,
            "revenue_growth": revenue_growth,
            "reaction_1d": reaction_1d,
            "reaction_30d": reaction_30d,
            "sentiment_label": sentiment_label,
        }
        records.append(features)

    return pd.DataFrame(records)

def train_sentiment_model(df: pd.DataFrame):
    feature_cols = [
        'volatility_30d', 'momentum_30d', 'momentum_90d',
        'avg_daily_return', 'eps_surprise_pct', 'revenue_growth'
    ]

    df[feature_cols] = df[feature_cols].fillna(0)
    df = df.dropna(subset=['sentiment_label'])
    df = df[df['sentiment_label'].isin(['positive', 'negative', 'neutral'])]

    if len(df) < 3:
        print("  Not enough data to train sentiment model")
        return None, None

    unique_classes = df['sentiment_label'].nunique()
    if unique_classes < 2:
        print(f"  Only {unique_classes} class found — adding synthetic samples")
        synthetic = df.sample(min(3, len(df)), random_state=42).copy()
        synthetic['sentiment_label'] = 'negative'
        synthetic['momentum_30d'] = synthetic['momentum_30d'] * -1
        synthetic['avg_daily_return'] = synthetic['avg_daily_return'] * -1
        df = pd.concat([df, synthetic], ignore_index=True)

    le = LabelEncoder()
    y = le.fit_transform(df['sentiment_label'])
    X = df[feature_cols].fillna(0)

    if len(df) < 10:
        model = GradientBoostingClassifier(
            n_estimators=50, max_depth=2, random_state=42
        )
        class_counts = Counter(y)
        total = sum(class_counts.values())
        sample_weights = [total / (len(class_counts) * class_counts[c]) for c in y]
        model.fit(X, y, sample_weight=sample_weights)
        print(f"  Sentiment model trained — {len(df)} samples")
        return model, le

    min_class_count = pd.Series(y).value_counts().min()
    stratify = y if min_class_count >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )

    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, random_state=42,
        subsample=0.8, min_samples_leaf=5
    )

    # Weight classes to handle imbalance
    class_counts = Counter(y_train)
    total = sum(class_counts.values())
    sample_weights = [total / (len(class_counts) * class_counts[c]) for c in y_train]
    model.fit(X_train, y_train, sample_weight=sample_weights)
    print(f"  Sentiment model trained — {len(df)} samples")
    return model, le

def train_reaction_model(df: pd.DataFrame):
    feature_cols = [
        'volatility_30d', 'momentum_30d', 'momentum_90d',
        'avg_daily_return', 'eps_surprise_pct', 'revenue_growth'
    ]

    df[feature_cols] = df[feature_cols].fillna(0)
    df = df.dropna(subset=['reaction_30d'])

    if len(df) < 3:
        print("  Not enough data to train reaction model")
        return None

    X = df[feature_cols].fillna(0)
    y = df['reaction_30d']

    model = GradientBoostingRegressor(
        n_estimators=100, max_depth=3, random_state=42
    )
    model.fit(X, y)
    print(f"  Reaction model trained — {len(df)} samples")
    return model

def generate_prediction(ticker: str, features_df: pd.DataFrame,
                        sentiment_model, label_encoder, reaction_model) -> dict:
    feature_cols = [
        'volatility_30d', 'momentum_30d', 'momentum_90d',
        'avg_daily_return', 'eps_surprise_pct', 'revenue_growth'
    ]

    if features_df.empty:
        return None

    latest = features_df.iloc[-1][feature_cols].fillna(0).values.reshape(1, -1)

    predicted_sentiment = "neutral"
    sentiment_confidence = 0.5
    predicted_reaction_1d = 0.0
    predicted_reaction_30d = 0.0

    if sentiment_model and label_encoder:
        try:
            pred_class = sentiment_model.predict(latest)[0]
            pred_proba = sentiment_model.predict_proba(latest)[0]
            predicted_sentiment = label_encoder.inverse_transform([pred_class])[0]
            sentiment_confidence = round(float(max(pred_proba)), 4)
        except:
            pass

    if reaction_model:
        try:
            predicted_reaction_30d = round(float(reaction_model.predict(latest)[0]), 2)
            predicted_reaction_1d = round(predicted_reaction_30d * 0.3, 2)
        except:
            pass

    from datetime import date
    today = date.today()
    quarter = (today.month - 1) // 3 + 1
    next_quarter = quarter + 1 if quarter < 4 else 1
    next_year = today.year if quarter < 4 else today.year + 1
    predicted_period = f"Q{next_quarter} {next_year}"

    return {
        "ticker": ticker,
        "predicted_period": predicted_period,
        "prediction_date": today,
        "predicted_sentiment": predicted_sentiment,
        "sentiment_confidence": sentiment_confidence,
        "predicted_reaction_1d": predicted_reaction_1d,
        "predicted_reaction_30d": predicted_reaction_30d,
        "features_used": ",".join(feature_cols),
        "model_version": "v1.0"
    }

def save_prediction(prediction: dict, engine):
    if not prediction:
        return
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO predictions
            (ticker, predicted_period, prediction_date, predicted_sentiment,
             sentiment_confidence, predicted_reaction_1d, predicted_reaction_30d,
             features_used, model_version)
            VALUES (:ticker, :predicted_period, :prediction_date, :predicted_sentiment,
                    :sentiment_confidence, :predicted_reaction_1d, :predicted_reaction_30d,
                    :features_used, :model_version)
            ON CONFLICT (ticker, predicted_period) DO UPDATE SET
                predicted_sentiment = EXCLUDED.predicted_sentiment,
                sentiment_confidence = EXCLUDED.sentiment_confidence,
                predicted_reaction_30d = EXCLUDED.predicted_reaction_30d,
                prediction_date = EXCLUDED.prediction_date
        """), prediction)
        conn.commit()

if __name__ == "__main__":
    print("Starting prediction pipeline...")
    create_tables(engine)

    os.makedirs("models", exist_ok=True)
    all_features = []

    print("\nBuilding features...")
    for ticker in COMPANIES:
        print(f"  {ticker}...")
        features = build_features(ticker)
        if not features.empty:
            all_features.append(features)

    if not all_features:
        print("No features built — exiting")
        exit()

    combined = pd.concat(all_features, ignore_index=True)
    print(f"\nTotal feature rows: {len(combined)}")
    print(f"Sentiment distribution:\n{combined['sentiment_label'].value_counts()}")

    print("\nTraining models...")
    sentiment_model, label_encoder = train_sentiment_model(combined)
    reaction_model = train_reaction_model(combined)

    if sentiment_model:
        joblib.dump(sentiment_model, "models/sentiment_model.pkl")
        joblib.dump(label_encoder, "models/label_encoder.pkl")
        print("Sentiment model saved")

    if reaction_model:
        joblib.dump(reaction_model, "models/reaction_model.pkl")
        print("Reaction model saved")

    print("\nGenerating predictions...")
    for ticker in COMPANIES:
        print(f"  Predicting {ticker}...")
        features = build_features(ticker)
        prediction = generate_prediction(
            ticker, features,
            sentiment_model, label_encoder, reaction_model
        )
        if prediction:
            save_prediction(prediction, engine)
            print(f"    → {prediction['predicted_sentiment']} "
                  f"({prediction['sentiment_confidence']*100:.1f}% confidence) "
                  f"| 30d reaction: {prediction['predicted_reaction_30d']:+.1f}%")

    print("\nPrediction pipeline complete!")