import requests
import yfinance as yf
import io
import base64
import os
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk

nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from collections import Counter
from newspaper import Article


class SentimentService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.news_url = "https://newsapi.org/v2/everything"
        self.vader = SentimentIntensityAnalyzer()

    def fetch_news_headlines(self, ticker: str, max_articles=3) -> list:
        params = {
            "q": ticker,
            "apiKey": self.api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_articles
        }
        response = requests.get(self.news_url, params=params)
        if response.status_code != 200:
            return []

        articles = response.json().get("articles", [])
        return [
            {
                "title": article["title"],
                "description": article["description"],
                "url": article["url"],
                "publishedAt": article["publishedAt"],
                "sentiment": self.analyze_sentiment(article["title"] + " " + str(article["description"])),
                "message_type": self.classify_message_type(article["title"] + " " + str(article["description"]))}
            for article in articles
        ]

    def fetch_full_article_text(self, url: str) -> str:
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            print(f"⚠️ Failed to fetch full article: {e}")
            return ""

    def analyze_sentiment(self, text: str) -> dict:
        return self.vader.polarity_scores(text)

    def classify_message_type(self, text: str) -> str:
        scores = self.vader.polarity_scores(text)
        if max(scores['pos'], scores['neg']) >= 0.4:
            return "Emotional"
        elif scores['neu'] >= 0.6:
            return "Informative"
        else:
            return "Informative"

    def enrich_articles(self, articles):
        enriched = []
        for a in articles:
            full_text = f"{a['title']} {a.get('description') or ''}"
            word_count = len(full_text.split())
            a['sentiment_label'] = (
                "😊 Positive" if a["sentiment"]["compound"] >= 0.2 else
                "😟 Negative" if a["sentiment"]["compound"] <= -0.2 else
                "😐 Neutral"
            )
            a['message_type'] = self.classify_message_type(full_text)  # ✅ Fix indentation
            enriched.append(a)
        return enriched

    def generate_emotion_info_histogram(self, articles):
        data = {'positive': {'emotional': 0, 'informative': 0},
                'neutral': {'emotional': 0, 'informative': 0},
                'negative': {'emotional': 0, 'informative': 0}}
        for a in articles:
            sentiment = (
                'positive' if a['sentiment']['compound'] >= 0.2 else
                'negative' if a['sentiment']['compound'] <= -0.2 else
                'neutral'
            )
            msg_type = a['message_type']
            data[sentiment][msg_type] += 1
        return data

    def get_sentiment_distribution(self, articles: list) -> str:
        emotional = sum(1 for a in articles if a["message_type"] == "Emotional")
        informative = sum(1 for a in articles if a["message_type"] == "Informative")

        labels = ['Informative', 'Emotional']
        counts = [informative, emotional]
        colors = ['#4e79a7', '#e15759']

        plt.figure(figsize=(6, 4))
        plt.bar(labels, counts, color=colors)
        plt.title("Sentiment Message Type Distribution")
        plt.ylabel("Number of Articles")

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        encoded_image = base64.b64encode(buf.read()).decode('utf-8')
        return encoded_image

    def generate_wordcloud(self, articles: list, ticker: str) -> None:
        text = " ".join((a["title"] or "") + " " + (a["description"] or "") for a in articles)
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(text)

        plt.figure(figsize=(8, 4))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout()

        # Save to static directory
        static_path = os.path.join("static", f"wordcloud_{ticker}.png")
        plt.savefig(static_path)
        plt.close()

    def get_banner_score(self, scores: list) -> str:
        avg = sum([s["compound"] for s in scores]) / len(scores) if scores else 0
        if avg >= 0.2:
            return "📈 Bullish"
        elif avg <= -0.2:
            return "📉 Bearish"
        else:
            return "😐 Neutral"

    def fetch_financial_ratios(self, ticker: str) -> dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "trailingPE": info.get("trailingPE", "N/A"),
                "forwardPE": info.get("forwardPE", "N/A"),
                "bookValue": info.get("bookValue", "N/A"),
                "ebitda": self.format_number(info.get("ebitda", "N/A")),
                "marketCap": self.format_number(info.get("marketCap", "N/A")),
                "previousClose": info.get("previousClose", "N/A"),
            }
        except Exception as e:
            print(f"⚠️ Error fetching financials for {ticker}: {e}")
            return {}

    def get_company_overview(self, ticker: str) -> str:
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get("longBusinessSummary", "No company overview available.")
        except:
            return "Company overview unavailable."

    def format_number(self, num):
        try:
            num = float(num)
            if num >= 1_000_000_000:
                return f"${num / 1_000_000_000:.2f}B"
            elif num >= 1_000_000:
                return f"${num / 1_000_000:.2f}M"
            elif num >= 1_000:
                return f"${num / 1_000:.2f}K"
            else:
                return f"${num:.2f}"
        except:
            return num
