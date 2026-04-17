import pandas as pd
from sqlalchemy import create_engine, text
from transformers import BartForConditionalGeneration, BartTokenizer
from transformers import pipeline
import yake
import warnings
warnings.filterwarnings("ignore")

# Database connection
DB_USER = "fraud_user"
DB_PASSWORD = "fraud_pass"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "fraud_db"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("Loading models... (this takes a minute on first run)")

# Load BART directly without pipeline
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
bart_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

# Financial sentiment model
sentiment_analyzer = pipeline(
    "text-classification",
    model="ProsusAI/finbert"
)

# Keyword extractor
kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)

print("Models loaded successfully")

def load_reports(engine):
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM financial_reports", conn)
    print(f"Loaded {len(df)} reports from PostgreSQL")
    return df

def summarize_text(text: str) -> str:
    inputs = tokenizer(
        text,
        return_tensors="pt",
        max_length=1024,
        truncation=True
    )
    summary_ids = bart_model.generate(
        inputs["input_ids"],
        max_length=150,
        min_length=50,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True
    )
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def analyze_sentiment(text: str) -> dict:
    words = text.split()
    if len(words) > 400:
        text = " ".join(words[:400])
    result = sentiment_analyzer(text, truncation=True, max_length=512)
    label = result[0]["label"]
    score = round(result[0]["score"], 4)
    return {"label": label, "score": score}

def extract_keywords(text: str) -> list:
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]

def create_results_table(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS report_analysis (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                company VARCHAR(100),
                period VARCHAR(20),
                summary TEXT,
                sentiment_label VARCHAR(20),
                sentiment_score FLOAT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()
    print("Results table created")

def save_results(results, engine):
    df = pd.DataFrame(results)
    df.to_sql("report_analysis", engine, if_exists="replace", index=False)
    print(f"Saved {len(df)} analysis results to PostgreSQL")

if __name__ == "__main__":
    df = load_reports(engine)
    create_results_table(engine)

    results = []
    for _, row in df.iterrows():
        print(f"\nAnalyzing {row['ticker']} — {row['period']}...")

        summary = summarize_text(row["text"])
        sentiment = analyze_sentiment(row["text"])
        keywords = extract_keywords(row["text"])

        print(f"  Summary: {summary[:100]}...")
        print(f"  Sentiment: {sentiment['label']} ({sentiment['score']})")
        print(f"  Keywords: {keywords[:5]}")

        results.append({
            "ticker": row["ticker"],
            "company": row["company"],
            "period": row["period"],
            "summary": summary,
            "sentiment_label": sentiment["label"],
            "sentiment_score": sentiment["score"],
            "keywords": ", ".join(keywords)
        })

    save_results(results, engine)
    print("\nAnalysis complete!")