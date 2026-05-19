import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
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

COLORS = {
    "AAPL": "#06d6a0",
    "MSFT": "#7c3aed",
    "GOOGL": "#ff6b35",
    "AMZN": "#ffd166",
    "NVDA": "#00b4d8",
    "TSLA": "#ef476f",
    "PLTR": "#118ab2",
    "SNOW": "#a8dadc",
    "DDOG": "#f77f00",
    "MDB": "#caffbf",
}

DARK_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#111111",
        font=dict(color="#f0f0f0", family="Inter, sans-serif"),
        xaxis=dict(gridcolor="#2a2a2a", zerolinecolor="#2a2a2a"),
        yaxis=dict(gridcolor="#2a2a2a", zerolinecolor="#2a2a2a"),
        legend=dict(bgcolor="#141414", bordercolor="#2a2a2a"),
        margin=dict(l=60, r=40, t=60, b=60)
    )
)

os.makedirs("static/charts", exist_ok=True)


def load_prices(ticker: str, days: int = 365) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""SELECT pm.date, pm.close, sp.volume, pm.daily_return,
                pm.volatility_30d, pm.momentum_30d
                FROM price_metrics pm
                LEFT JOIN stock_prices sp
                ON pm.ticker = sp.ticker AND pm.date = sp.date
                WHERE pm.ticker = '{ticker}'
                ORDER BY pm.date DESC
                LIMIT {days}""",
            conn
        )
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date')


def load_events(ticker: str) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            f"""SELECT date, event_type, price_change_pct, description
                FROM market_events
                WHERE ticker = '{ticker}'
                ORDER BY date""",
            conn
        )
    df['date'] = pd.to_datetime(df['date'])
    return df


def chart_price_history(ticker: str) -> str:
    prices = load_prices(ticker, days=756)
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=756)
    prices = prices[prices['date'] >= cutoff]
    events = load_events(ticker)

    # Filter events to same window
    if not events.empty:
        events = events[events['date'] >= cutoff]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.05,
        subplot_titles=[f"{ticker} — Price History (3 Years)", "30-Day Volatility %"]
    )

    fig.add_trace(go.Scatter(
        x=prices['date'],
        y=prices['close'],
        mode='lines',
        name='Close Price',
        line=dict(color=COLORS.get(ticker, '#06d6a0'), width=2),
        hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
    ), row=1, col=1)

    if not events.empty:
        surges = events[events['event_type'] == 'major_surge']
        drops = events[events['event_type'] == 'major_drop']

        if not surges.empty:
            surge_prices = []
            for d in surges['date']:
                match = prices[prices['date'] == d]
                surge_prices.append(float(match['close'].values[0]) if not match.empty else None)
            fig.add_trace(go.Scatter(
                x=surges['date'],
                y=surge_prices,
                mode='markers',
                name='Major Surge',
                marker=dict(color='#06d6a0', size=8, symbol='triangle-up'),
                hovertemplate='%{x}<br>Surge: %{customdata:.1f}%<extra></extra>',
                customdata=surges['price_change_pct']
            ), row=1, col=1)

        if not drops.empty:
            drop_prices = []
            for d in drops['date']:
                match = prices[prices['date'] == d]
                drop_prices.append(float(match['close'].values[0]) if not match.empty else None)
            fig.add_trace(go.Scatter(
                x=drops['date'],
                y=drop_prices,
                mode='markers',
                name='Major Drop',
                marker=dict(color='#ef476f', size=8, symbol='triangle-down'),
                hovertemplate='%{x}<br>Drop: %{customdata:.1f}%<extra></extra>',
                customdata=drops['price_change_pct']
            ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=prices['date'],
        y=prices['volatility_30d'],
        mode='lines',
        name='30d Volatility',
        line=dict(color='#ffd166', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(255, 209, 102, 0.1)',
        hovertemplate='%{x}<br>Volatility: %{y:.2f}%<extra></extra>'
    ), row=2, col=1)

    fig.update_layout(
        **DARK_TEMPLATE['layout'].to_plotly_json(),
        height=500,
        showlegend=True,
        hovermode='x unified'
    )
    fig.update_yaxes(tickprefix='$', row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=2, col=1)

    path = f"static/charts/{ticker}_price_history.json"
    with open(path, 'w') as f:
        f.write(fig.to_json(engine='json'))

    print(f"  Saved {path}")
    return path


def chart_earnings_reactions() -> str:
    all_reactions = []
    for ticker in COMPANIES:
        with engine.connect() as conn:
            df = pd.read_sql(
                f"""SELECT period, period_date, reaction_30d_pct
                    FROM earnings_reactions
                    WHERE ticker = '{ticker}'
                    ORDER BY period_date DESC
                    LIMIT 12""",
                conn
            )
        if not df.empty:
            df = df[df['reaction_30d_pct'].notna()]
            if df.empty:
                continue
            df['ticker'] = ticker
            df = df.drop_duplicates(subset=['period'], keep='first')
            all_reactions.append(df[['ticker', 'period', 'reaction_30d_pct']].head(8))

    if not all_reactions:
        return ""

    df = pd.concat(all_reactions, ignore_index=True)

    if df.empty or df['reaction_30d_pct'].isna().all():
        print("  No valid reaction data for heatmap")
        return ""

    pivot = df.pivot_table(
        index='ticker',
        columns='period',
        values='reaction_30d_pct',
        aggfunc='mean'
    )
    pivot = pivot[sorted(pivot.columns, key=lambda x: (x.split()[-1], x.split()[0]))]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.0, '#ef476f'],
            [0.5, '#141414'],
            [1.0, '#06d6a0']
        ],
        zmid=0,
        text=[[f"{v:.1f}%" if not pd.isna(v) else ""
               for v in row] for row in pivot.values],
        texttemplate="%{text}",
        hovertemplate='%{y} | %{x}<br>30d reaction: %{z:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        **DARK_TEMPLATE['layout'].to_plotly_json(),
        title="30-Day Price Reaction After Earnings (Last 8 Quarters)",
        height=450,
        xaxis_title="Quarter",
        yaxis_title="Company"
    )

    path = "static/charts/earnings_heatmap.json"
    with open(path, 'w') as f:
        f.write(fig.to_json(engine='json'))
    print(f"  Saved {path}")
    return path


def chart_volatility_comparison() -> str:
    rows = []
    for ticker in COMPANIES:
        prices = load_prices(ticker, days=365)
        if not prices.empty:
            rows.append({
                "ticker": ticker,
                "volatility": round(float(prices['volatility_30d'].mean() or 0), 2),
                "avg_return": round(float(prices['daily_return'].mean() or 0), 3),
                "momentum_30d": round(float(prices['momentum_30d'].iloc[-1] or 0), 2)
            })

    df = pd.DataFrame(rows).sort_values('volatility', ascending=False)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["30-Day Volatility (%)", "30-Day Momentum (%)"]
    )

    colors = [COLORS.get(t, '#06d6a0') for t in df['ticker']]

    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=df['volatility'],
        marker_color=colors,
        name='Volatility',
        hovertemplate='%{x}<br>Volatility: %{y:.2f}%<extra></extra>'
    ), row=1, col=1)

    momentum_colors = ['#06d6a0' if m >= 0 else '#ef476f' for m in df['momentum_30d']]
    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=df['momentum_30d'],
        marker_color=momentum_colors,
        name='30d Momentum',
        hovertemplate='%{x}<br>Momentum: %{y:.2f}%<extra></extra>'
    ), row=1, col=2)

    fig.update_layout(
        **DARK_TEMPLATE['layout'].to_plotly_json(),
        title="Volatility & Momentum Comparison — All 10 Companies",
        height=400,
        showlegend=False
    )

    path = "static/charts/volatility_comparison.json"
    with open(path, 'w') as f:
        f.write(fig.to_json(engine='json'))

    print(f"  Saved {path}")
    return path


def chart_predictions() -> str:
    with engine.connect() as conn:
        df = pd.read_sql(
            """SELECT ticker, predicted_sentiment, sentiment_confidence,
               predicted_reaction_30d
               FROM predictions
               ORDER BY predicted_reaction_30d DESC""",
            conn
        )

    if df.empty:
        return ""

    sentiment_colors = {
        'positive': '#06d6a0',
        'negative': '#ef476f',
        'neutral': '#ffd166'
    }

    colors = [sentiment_colors.get(s, '#888888') for s in df['predicted_sentiment']]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Predicted 30-Day Price Reaction", "Sentiment Confidence (%)"]
    )

    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=df['predicted_reaction_30d'],
        marker_color=colors,
        name='30d Reaction',
        hovertemplate='%{x}<br>Predicted: %{y:+.1f}%<extra></extra>'
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df['ticker'],
        y=(df['sentiment_confidence'] * 100).round(1),
        marker_color=colors,
        name='Confidence',
        hovertemplate='%{x}<br>Confidence: %{y:.1f}%<extra></extra>'
    ), row=1, col=2)

    fig.update_layout(
        **DARK_TEMPLATE['layout'].to_plotly_json(),
        title="Next Quarter Predictions — All 10 Companies",
        height=400,
        showlegend=False
    )
    fig.update_yaxes(ticksuffix='%', row=1, col=1)
    fig.update_yaxes(ticksuffix='%', row=1, col=2)

    path = "static/charts/predictions.json"
    with open(path, 'w') as f:
        f.write(fig.to_json(engine='json'))

    print(f"  Saved {path}")
    return path


def chart_normalized_prices() -> str:
    fig = go.Figure()

    for ticker in COMPANIES:
        prices = load_prices(ticker, days=365)
        if prices.empty:
            continue
        first_price = prices['close'].iloc[0]
        if first_price == 0:
            continue
        normalized = (prices['close'] / first_price) * 100
        fig.add_trace(go.Scatter(
            x=prices['date'],
            y=normalized,
            mode='lines',
            name=ticker,
            line=dict(color=COLORS.get(ticker, '#888888'), width=1.5),
            hovertemplate=f'{ticker}<br>%{{x}}<br>%{{y:.1f}}% of start<extra></extra>'
        ))

    fig.add_hline(y=100, line_dash="dash",
                  line_color="#444444", annotation_text="Baseline")

    fig.update_layout(
        **DARK_TEMPLATE['layout'].to_plotly_json(),
        title="Normalized Price Performance — Last 12 Months (Base = 100)",
        height=450,
        xaxis_title="Date",
        yaxis_title="Normalized Price (%)",
        hovermode='x unified'
    )

    path = "static/charts/normalized_prices.json"
    with open(path, 'w') as f:
        f.write(fig.to_json(engine='json'))

    print(f"  Saved {path}")
    return path


if __name__ == "__main__":
    print("Generating visualizations...")

    print("\nIndividual price charts:")
    for ticker in COMPANIES:
        print(f"  {ticker}...")
        chart_price_history(ticker)

    print("\nSummary charts:")
    chart_earnings_reactions()
    chart_volatility_comparison()
    chart_predictions()
    chart_normalized_prices()

    print("\nAll charts saved to static/charts/")