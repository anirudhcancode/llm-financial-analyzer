import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_db"
)

engine = create_engine(DATABASE_URL)

reports = [
    {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "period": "Q1 2024",
        "type": "Earnings Call",
        "text": """Apple reported first quarter results with revenue of $119.6 billion,
        up 2 percent year over year. iPhone revenue was $69.7 billion, Services revenue
        reached an all-time high of $23.1 billion, up 11 percent year over year.
        Tim Cook stated that the company is thrilled with the performance and sees
        strong momentum in emerging markets. Gross margin was 45.9 percent,
        operating income was $40.4 billion. The company returned over $27 billion
        to shareholders during the quarter. Management expressed confidence in the
        upcoming product pipeline and AI integration across all product lines.
        However, China revenue declined 13 percent amid increased competition from
        local manufacturers. Mac revenue declined 1 percent. iPad revenue declined
        25 percent year over year. The company guided for low to mid single digit
        revenue growth in the next quarter."""
    },
    {
        "ticker": "MSFT",
        "company": "Microsoft Corporation",
        "period": "Q2 2024",
        "type": "Earnings Call",
        "text": """Microsoft delivered strong second quarter results with total revenue
        of $62.0 billion, up 18 percent year over year. Cloud revenue surpassed
        expectations with Azure growing 28 percent. The company highlighted that
        AI services are becoming a significant revenue driver across all segments.
        Satya Nadella emphasized that Microsoft Copilot is being adopted rapidly
        across enterprise customers. Operating income increased 33 percent to
        $27.0 billion. Net income was $21.9 billion, up 33 percent. The Intelligent
        Cloud segment revenue was $25.9 billion, up 21 percent. Productivity and
        Business Processes revenue was $19.2 billion, up 13 percent. The company
        raised its full year guidance citing strong AI demand and cloud adoption.
        Capital expenditure increased significantly to support AI infrastructure buildout."""
    },
    {
        "ticker": "GOOGL",
        "company": "Alphabet Inc.",
        "period": "Q4 2023",
        "type": "Earnings Call",
        "text": """Alphabet reported fourth quarter revenue of $86.3 billion, up 13 percent
        year over year. Google Search revenue grew 13 percent to $48.0 billion.
        YouTube advertising revenue was $9.2 billion, up 16 percent. Google Cloud
        revenue reached $9.2 billion, up 26 percent, with the segment turning profitable.
        Sundar Pichai highlighted the company's progress in AI with Gemini model
        deployments across products. The company announced a $70 billion share buyback
        program. Operating margin improved to 27 percent. However, the company faces
        ongoing regulatory scrutiny in multiple jurisdictions regarding its search
        monopoly. Headcount reductions continued as part of efficiency measures.
        Other Bets segment reported losses of $1.6 billion. Management expressed
        optimism about AI-driven growth opportunities in 2024."""
    },
    {
        "ticker": "AMZN",
        "company": "Amazon.com Inc.",
        "period": "Q3 2023",
        "type": "Earnings Call",
        "text": """Amazon reported third quarter net sales of $143.1 billion, up 13 percent
        year over year. AWS revenue grew 12 percent to $23.4 billion, showing
        reacceleration after several quarters of deceleration. North America segment
        operating income was $4.3 billion compared to a loss in the prior year period.
        Andy Jassy highlighted operational efficiency improvements and cost reduction
        initiatives. Advertising revenue grew 26 percent to $12.1 billion.
        The company is investing heavily in generative AI capabilities for AWS.
        Operating income for the quarter was $11.2 billion compared to $2.5 billion
        in the prior year. Free cash flow improved significantly. The company guided
        for Q4 net sales between $160 billion and $167 billion. Prime membership
        continues to grow globally. Logistics network optimization is yielding
        significant cost savings."""
    },
    {
        "ticker": "NVDA",
        "company": "NVIDIA Corporation",
        "period": "Q3 2024",
        "type": "Earnings Call",
        "text": """NVIDIA reported record third quarter revenue of $18.1 billion, up 206 percent
        year over year and up 34 percent sequentially. Data Center revenue was a record
        $14.5 billion, up 279 percent year over year driven by AI chip demand.
        Jensen Huang stated that the global AI infrastructure buildout is driving
        unprecedented demand for NVIDIA's products. Gaming revenue was $2.9 billion,
        up 81 percent. Gross margin expanded to 74.6 percent. The company announced
        strong demand for the upcoming Blackwell architecture. Net income was $9.2 billion
        compared to $680 million in the prior year period. The company raised guidance
        significantly above analyst expectations. Supply constraints remain a challenge
        despite aggressive capacity expansion with manufacturing partners.
        NVIDIA's CUDA ecosystem continues to create strong competitive moats."""
    }
]

analysis_results = [
    {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "period": "Q1 2024",
        "summary": "Apple reported first quarter results with revenue of $119.6 billion. iPhone revenue was $69.7 billion, Services revenue reached an all-time high of $23.1 billion. China revenue declined 13 percent amid increased competition from local manufacturers.",
        "sentiment_label": "negative",
        "sentiment_score": 0.9488,
        "keywords": "percent year, year, Apple reported, percent, billion, revenue, revenue declined, declined, Services revenue, company"
    },
    {
        "ticker": "MSFT",
        "company": "Microsoft Corporation",
        "period": "Q2 2024",
        "summary": "Microsoft delivered strong second quarter results with total revenue of $62.0 billion, up 18 percent year over year. Cloud revenue surpassed expectations with Azure growing 28 percent. The company raised its full year guidance citing strong AI demand and cloud adoption.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9537,
        "keywords": "billion, quarter results, percent, Microsoft delivered, revenue, Azure growing, Microsoft Copilot, total revenue, Microsoft, Cloud"
    },
    {
        "ticker": "GOOGL",
        "company": "Alphabet Inc.",
        "period": "Q4 2023",
        "summary": "Alphabet reported fourth quarter revenue of $86.3 billion. Google Search revenue grew 13 percent to $48.0 billion. YouTube advertising revenue was $9.2 billion, up 16 percent. Google Cloud revenue was up 26 percent, with the segment turning profitable.",
        "sentiment_label": "positive",
        "sentiment_score": 0.7422,
        "keywords": "fourth quarter, billion, percent, percent year, year, revenue, quarter revenue, Alphabet reported, reported fourth, company"
    },
    {
        "ticker": "AMZN",
        "company": "Amazon.com Inc.",
        "period": "Q3 2023",
        "summary": "Amazon reported third quarter net sales of $143.1 billion, up 13 percent year over year. North America segment operating income was $4.3 billion. Free cash flow improved significantly.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9598,
        "keywords": "billion, Amazon reported, percent, billion compared, year, revenue grew, percent year, prior year, AWS, Amazon"
    },
    {
        "ticker": "NVDA",
        "company": "NVIDIA Corporation",
        "period": "Q3 2024",
        "summary": "NVIDIA reported record third quarter revenue of $18.1 billion, up 206 percent year over year and up 34 percent sequentially. Data Center revenue was a record $14.5 billion, driven by AI chip demand. The company raised guidance significantly above analyst expectations.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9572,
        "keywords": "percent, percent sequentially, percent year, year, NVIDIA reported, billion, NVIDIA, reported record, Center revenue, quarter revenue"
    }
]

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS financial_reports (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10),
                company VARCHAR(100),
                period VARCHAR(20),
                type VARCHAR(50),
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
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
    print("Tables created successfully")

def ingest_reports(engine):
    df = pd.DataFrame(reports)
    df.to_sql("financial_reports", engine, if_exists="replace", index=False)
    print(f"Ingested {len(df)} financial reports")

def ingest_analysis(engine):
    df = pd.DataFrame(analysis_results)
    df.to_sql("report_analysis", engine, if_exists="replace", index=False)
    print(f"Ingested {len(df)} analysis results")

if __name__ == "__main__":
    create_tables(engine)
    ingest_reports(engine)
    ingest_analysis(engine)
    print("Ingestion complete!")