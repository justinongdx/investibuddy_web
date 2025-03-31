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
You're a helpful financial assistant.

Here is a portfolio:

{formatted_portfolio_text}

Suggest for each: Buy, Hold, or Sell, and explain briefly why — considering sector, diversification, and price performance.
Respond in bullet points.
"""
    response = model.generate_content(prompt)
    return response.text.strip()
