# StockLens — Stock Market Analysis Web Application

**StockLens** ("*Analyze. Understand. Track.*") is a production-grade financial analytics and stock market tracking platform running locally on localhost. It combines Python Flask, real-time market data from Yahoo Finance via `yfinance`, scientific calculations with `pandas` and `numpy`, responsive modern financial dashboard UI, and interactive charts via `Plotly.js`.

---

## 🌟 Key Features

1. **Market Overview**:
   - Real-time performance of major global & Indian indices: **S&P 500 (`^GSPC`)**, **NASDAQ (`^IXIC`)**, **Dow Jones (`^DJI`)**, **NIFTY 50 (`^NSEI`)**, and **SENSEX (`^BSESN`)**.
   - Mini sparkline charts for visual intraday/5-day trajectory.
2. **Universal Ticker Search**:
   - Works with US tickers (**AAPL**, **MSFT**, **GOOGL**, **AMZN**, **TSLA**, **NVDA**, **META**, **NFLX**).
   - Works with Indian tickers (**RELIANCE.NS**, **TCS.NS**, **INFY.NS**, **HDFCBANK.NS**, **ICICIBANK.NS**).
   - Works with Asian & Global tickers (**005930.KS** for Samsung Electronics, etc.).
   - Gracefully handles invalid tickers without crashing.
3. **Interactive Price Charts**:
   - Candlestick OHLC + Volume charts with multi-period selection (**1D**, **5D**, **1M**, **3M**, **6M**, **1Y**, **5Y**, **MAX**).
   - Zoom, pan, hover crosshairs, and responsive layout.
4. **Technical Analysis Engine**:
   - **Simple Moving Averages**: SMA 20, SMA 50, SMA 200.
   - **Exponential Moving Averages**: EMA 20.
   - **RSI 14**: Relative Strength Index with 70/30 overbought/oversold indicator thresholds.
   - **MACD**: MACD Line, Signal Line, and colored Histogram.
   - **Bollinger Bands**: Upper band, 20-day SMA, Lower band.
   - **Volatility & Returns**: Annualized historical volatility, 1W, 1M, 3M, 1Y percentage returns.
5. **Quantitative Summary**:
   - Objective, factual analytical breakdown (e.g., "Above SMA 50", "RSI: 58 (Neutral)", "Volatility: 24.5%").
   - Strictly neutral calculations without speculative or financial advice claims.
6. **Fundamental Analysis & Financial Statements**:
   - Market Cap, Trailing & Forward P/E, EPS, Price-to-Book, Price-to-Sales, Enterprise Value, Profit & Operating Margins, Return on Equity, Debt-to-Equity, Free Cash Flow, Dividend Yield, Beta.
   - **Income Statement**, **Balance Sheet**, and **Cash Flow** with **Annual** and **Quarterly** view toggling.
   - Company profile, industry, sector, full-time employees, website, and business summary.
7. **Multi-Stock Comparison**:
   - Side-by-side comparison of up to 6 stocks at once (e.g. `AAPL, MSFT, NVDA, GOOGL`).
   - Normalized 1-year performance comparison chart (`%` return basis from t=0).
   - Matrix of valuation, margins, volatility, and returns.
8. **Watchlist & Portfolio Tracker**:
   - Add stocks to a personal watchlist with live prices and daily change indicators.
   - Portfolio tracker: record ticker, quantity, purchase price, and purchase date.
   - Automatically calculates total invested capital, current live market value, profit/loss ($), and percentage return.
   - Tracking and educational purposes only (does not execute real brokerage trades).
9. **User Authentication**:
   - Register and Login functionality with salted SHA-256 password hashing.
   - SQLite local database storage (`data/stocklens.db`), structured for straightforward migration to PostgreSQL or MongoDB.
10. **Data Caching & Performance**:
    - In-memory thread-safe TTL cache (`DATA_CACHE_SECONDS=300`) to avoid redundant Yahoo Finance rate limits.
    - Refresh button to clear and reload fresh quotes.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, Flask 3.0+
- **Database**: SQLite (built-in, zero external setup needed)
- **Market Data**: `yfinance`
- **Data Science**: `pandas`, `numpy`
- **Configuration**: `python-dotenv`
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+)
- **UI Frameworks**: Bootstrap 5, Bootstrap Icons
- **Charting**: Plotly.js 2.27

---

## 📁 Project Structure

```
stock-analysis/
│
├── app.py                      # Flask entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── .env.example                # Example environment template
├── README.md                   # Project documentation
│
├── backend/
│   ├── __init__.py             # Flask application factory, blueprints & CORS
│   ├── database.py             # SQLite connection & schema initializer
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py            # Page view routes (/, /stock/<t>, /dashboard, /compare, /login, /register)
│   │   ├── stocks.py           # /api/stock endpoints (info, price, history, financials, news, search, market)
│   │   ├── analysis.py         # /api/stock/<t>/analysis & /api/compare
│   │   └── auth.py             # /api/auth (register, login, logout), /api/watchlist, /api/portfolio
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── yahoo_service.py    # Centralized yfinance API wrapper with fallback & cache
│   │   ├── analysis_service.py # Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, Volatility)
│   │   └── cache_service.py    # Thread-safe in-memory TTL caching
│   │
│   └── utils/
│       ├── __init__.py
│       └── validators.py       # Ticker, input, username, and sanitization validators
│
├── templates/
│   ├── base.html               # Base layout, navbar, theme toggle, toast notifications
│   ├── index.html              # Homepage with hero search, market indices, popular stocks
│   ├── stock.html              # Comprehensive stock detail & technical analysis
│   ├── dashboard.html          # Portfolio tracker & Watchlist management
│   ├── compare.html            # Multi-stock side-by-side comparison & normalized charts
│   ├── login.html              # User login
│   └── register.html           # User registration
│
├── static/
│   ├── css/
│   │   └── style.css           # Premium financial dashboard styling (dark/light themes, glassmorphism)
│   │
│   └── js/
│       ├── app.js              # Shared API client, theme toggle, formatters, toasts, auth listener
│       ├── dashboard.js        # Dashboard portfolio & watchlist manager
│       └── stock.js            # Stock details, Plotly candlestick, RSI, MACD charts & statements
│
└── data/
    └── stocklens.db            # SQLite database (auto-generated)
```

---

## 🚀 Installation & Running on Localhost (Windows Instructions)

Follow these steps in your Windows terminal (PowerShell, Command Prompt, or VS Code integrated terminal):

### 1. Open Terminal in the Project Directory
```powershell
cd "c:\Users\Dell\Desktop\ml project\stock-analysis"
```

### 2. (Optional but recommended) Create and Activate a Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

*Note: If PowerShell shows an execution policy warning when running `activate`, you can run:*
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
```

### 3. Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
A default `.env` is already configured:
```ini
SECRET_KEY=stocklens-dev-secret-key-change-in-production
DATA_CACHE_SECONDS=300
DEBUG=True
```

### 5. Run the Application
```powershell
python app.py
```

You will see:
```
 * Serving Flask app 'backend'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### 6. Open in Your Browser
Visit:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)** or **[http://localhost:5000](http://localhost:5000)**

---

## 🔎 How to Search and Add Stocks

Yahoo Finance uses specific symbol suffixes for different international exchanges:

| Exchange | Region | Suffix Example | Example Companies |
| :--- | :--- | :--- | :--- |
| **US Exchanges** (NASDAQ, NYSE) | United States | None | `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `TSLA`, `NVDA`, `META` |
| **National Stock Exchange** (NSE) | India | `.NS` | `RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`, `ICICIBANK.NS` |
| **Bombay Stock Exchange** (BSE) | India | `.BO` | `RELIANCE.BO`, `TCS.BO`, `INFY.BO` |
| **Korea Exchange** (KRX) | South Korea | `.KS` | `005930.KS` (Samsung Electronics) |
| **London Stock Exchange** (LSE) | United Kingdom | `.L` | `SHEL.L`, `AZN.L` |
| **Toronto Stock Exchange** (TSX) | Canada | `.TO` | `SHOP.TO`, `RY.TO` |

---

## 🧪 Testing Verification Checklist

After launching the application, you can test the following:

1. **Homepage (`http://127.0.0.1:5000/`)**:
   - Major indices (S&P 500, NASDAQ, Dow Jones, NIFTY 50, SENSEX) load with live values and sparklines.
   - Popular stocks show live quotes.
   - Dark/light mode button in the top navbar toggles theme seamlessly.
2. **Stock Analysis (`http://127.0.0.1:5000/stock/AAPL`)**:
   - Candlestick chart loads with volume; test timeframe buttons (1D, 5D, 1M, 6M, 1Y, MAX).
   - Technical analysis tab displays RSI, MACD, Moving Averages, and Quantitative Summary.
   - Fundamentals tab shows P/E, EPS, Market Cap, Margins, and Company Overview.
   - Financials tab toggles between Income Statement, Balance Sheet, Cash Flow, and Annual/Quarterly.
   - News tab loads real news articles from Yahoo Finance.
3. **Indian Ticker (`http://127.0.0.1:5000/stock/RELIANCE.NS`)**:
   - Displays price in INR (`₹`), company information, and technical indicators.
4. **Invalid Ticker (`http://127.0.0.1:5000/stock/INVALIDXYZ`)**:
   - Friendly error card displayed without crashing or exposing Python stack traces.
5. **Comparison (`http://127.0.0.1:5000/compare`)**:
   - Compare `AAPL, MSFT, NVDA, GOOGL` or click "India Bluechips" preset.
   - View normalized return lines and side-by-side metric tables.
6. **Authentication & Portfolio (`http://127.0.0.1:5000/dashboard`)**:
   - Register a new account (`/register`).
   - Add tickers to your watchlist.
   - Add holdings to your portfolio (quantity, purchase price, date) and inspect live profit/loss calculations.

---

## 💡 Troubleshooting

- **Temporary Yahoo Finance Network / Rate Limit**:
  - The application includes an automatic in-memory cache (`DATA_CACHE_SECONDS=300`) to minimize calls to Yahoo Finance. If an individual request times out or experiences Yahoo Finance rate limits, click the **Refresh** button or wait 60 seconds.
- **Port 5000 already in use**:
  - You can change the port in `app.py`: `app.run(port=5001)` or terminate the process using port 5000.
- **Data Disclaimer**:
  - Market data is provided through Yahoo Finance / `yfinance`. StockLens is an analysis and tracking tool and does not provide financial or investment advice.
