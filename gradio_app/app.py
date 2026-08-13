import os
import gradio as gr
import yake
from transformers import BartForConditionalGeneration, BartTokenizer, pipeline

# Same models and inference code as src/analyze.py — loaded once at startup,
# nothing retrained.
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
bart_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

sentiment_analyzer = pipeline("text-classification", model="ProsusAI/finbert")

kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=10)


def summarize_text(text: str) -> str:
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = bart_model.generate(
        inputs["input_ids"],
        max_length=150,
        min_length=50,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True,
    )
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)


def analyze_sentiment(text: str) -> dict:
    words = text.split()
    if len(words) > 400:
        text = " ".join(words[:400])
    result = sentiment_analyzer(text, truncation=True, max_length=512)
    return {"label": result[0]["label"], "score": round(result[0]["score"], 4)}


def extract_keywords(text: str) -> list:
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]


SENTIMENT_MARKER = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}


def analyze(report_text):
    if not report_text or not report_text.strip():
        return "*Paste an earnings-report excerpt above and submit.*", "", ""

    summary = summarize_text(report_text)
    sentiment = analyze_sentiment(report_text)
    keywords = extract_keywords(report_text)

    marker = SENTIMENT_MARKER.get(sentiment["label"].lower(), "⚪")
    sentiment_md = (
        f"### {marker} {sentiment['label'].title()}\n"
        f"Confidence: **{sentiment['score'] * 100:.2f}%**"
    )
    keywords_md = "\n".join(f"- {kw}" for kw in keywords)

    return summary, sentiment_md, keywords_md


EXAMPLE_TEXT = (
    "Apple reported second quarter 2024 revenue of $90.8 billion, down 4% "
    "year over year. China revenue declined 13% to $16.4 billion, driven by "
    "increased competition from local smartphone makers. iPad revenue fell "
    "25% versus the prior year quarter. Services revenue, however, grew 14% "
    "to a record $23.9 billion, and the company announced a record $110 "
    "billion share buyback program. Management pointed to ongoing softness "
    "in Greater China and iPad demand as the primary drags on the quarter, "
    "while highlighting the Services segment and an expanding installed "
    "base as offsetting strengths going into the back half of the year."
)

description = """
Paste (or edit) an earnings-report excerpt and submit — this runs the same
BART summarization, FinBERT sentiment, and YAKE keyword extraction code as
`src/analyze.py`, live, on whatever text you give it. This is the live
on-demand inference the current Render deployment can't do on its free CPU
tier (that version serves 5 pre-computed reports from cache); here it
actually runs.

Model loading takes 20-60 seconds on a cold start — the interface will
respond as soon as it's ready.
"""

with gr.Blocks(title="LLM Financial Report Analyzer — Live Inference") as demo:
    gr.Markdown("# LLM Financial Report Analyzer — Live Inference")
    gr.Markdown(description)

    report_text = gr.Textbox(
        label="Earnings report excerpt",
        value=EXAMPLE_TEXT,
        lines=8,
    )
    submit_btn = gr.Button("Analyze", variant="primary")

    with gr.Row():
        with gr.Column():
            gr.Markdown("**Summary (BART)**")
            summary_out = gr.Markdown()
        with gr.Column():
            gr.Markdown("**Sentiment (FinBERT)**")
            sentiment_out = gr.Markdown()
        with gr.Column():
            gr.Markdown("**Keywords (YAKE)**")
            keywords_out = gr.Markdown()

    submit_btn.click(
        fn=analyze,
        inputs=[report_text],
        outputs=[summary_out, sentiment_out, keywords_out],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
