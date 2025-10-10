📊 InvestiBuddy – Web-Based Stock Portfolio Dashboard

InvestiBuddy is a Flask-based stock portfolio web application that helps beginner investors monitor their holdings and gain insights through AI-powered sentiment analysis. 
Users can create portfolios, add stocks, visualize sector allocation, and explore financial and emotional news sentiment for informed decision-making.

---
Features

1. Portfolio Management
- Create & manage multiple portfolios
- Add transactions (buy/sell) for each stock
- View unrealised and realised P&L
- Export to Excel

2. Visual Dashboards
- **Portfolio Performance Graph**: Line chart over selected timeframes
- **Sector Allocation Pie Chart**: Visualizes weight by sector using Chart.js

3. News & Sentiment Insights
- Pulls real-time news using **NewsAPI**
- Sentiment classification using **VADER**
- Emotional vs Informative classification
- Auto-generated **WordCloud** and **Histogram**
- Financial ratios & company overview from **yFinance**
- Interactive 5-tab layout (News | Sentiment | WordCloud | Fundamentals | About)

4. Gemini AI Recommendations
- Converts portfolio metrics into prompts for Gemini API
- Returns text-based investment insights per user portfolio

5. Authentication
- Login/Logout with session-based route protection
- User registration with risk profile input

---
Project Structure

```bash
investibuddy_web/
│
├── app.py                     # Main Flask app with routes
├── requirements.txt           # Python dependencies
├── static/                    # WordCloud images, CSS
├── templates/                 # HTML files using Jinja
├── models/                    # Database and helper logic
│   ├── entities.py
│   ├── database_manager.py
│   ├── portfolio_manager.py
│   ├── portfolio_history.py
│   ├── user_manager.py
│   └── yfinance_source.py
├── sentiment_service.py       # Core logic for news enrichment
└── ...
```

---
Tech Stack
Frontend: HTML5, Bootstrap 5, Jinja templating, Chart.js
Backend: Python, Flask
APIs: NewsAPI, yFinance, Gemini (optional)
NLP: NLTK VADER Sentiment Analyzer
Data Viz: Matplotlib, WordCloud
Database: SQLite

---
Contributors:
Anthony, Justin, Sasha, Lisa, Long
