import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# You can swap this to gemini-1.5-flash-latest for faster responses
model = genai.GenerativeModel("models/gemini-1.5-pro-latest")


def format_portfolio_for_gemini(symbol_metrics):
    summary_lines = []
    for m in symbol_metrics:
        summary_lines.append(
            f"Ticker: {m['ticker']}, Sector: {m['sector']}, Price: ${m['current_price']}, "
            f"Shares: {m['current_shares']}, Value: ${m['current_value']}"
        )
    return "\n".join(summary_lines)


def get_gemini_recommendation(formatted_portfolio_text):
    prompt = f"""
You are an intelligent and professional financial assistant.

A user has the following stock portfolio:

{formatted_portfolio_text}

Your task:
- Analyse the portfolio for sector concentration, lack of diversification, or overweight positions.
- Provide 1–2 actionable, concise suggestions to help balance or strengthen the portfolio.
- If diversification is lacking, suggest specific sectors or asset classes the user might consider.
- Use a clear, formal tone suitable for a finance dashboard.
- Do NOT use markdown, emojis, or any special formatting — just plain text.

Output should be under 100 words and easy to display inside a UI card.
"""

    response = model.generate_content(prompt)
    return response.text.strip()

