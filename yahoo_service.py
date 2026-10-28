"""
Yahoo Finance Service for StockLens.
Centralizes all yfinance API calls with robust error handling, caching,
and real market data sanitization.
"""

import logging
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
from backend.services.cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


def _get_timestamp_str():
    """Get current UTC timestamp formatted ISO."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def get_stock_info(ticker_symbol):
    """Fetch comprehensive company information."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'info_{ticker_symbol}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = {}
        try:
            info = ticker.info or {}
        except Exception as e:
            logger.warning(f"Could not load ticker.info for {ticker_symbol}: {e}")

        # Check fast_info fallback for price data if info is empty or missing prices
        fast_price = None
        fast_prev_close = None
        try:
            fast = getattr(ticker, 'fast_info', None)
            if fast:
                fast_price = getattr(fast, 'last_price', None)
                fast_prev_close = getattr(fast, 'previous_close', None)
        except Exception:
            pass

        regular_price = info.get('regularMarketPrice') or info.get('currentPrice') or fast_price
        prev_close = info.get('previousClose') or fast_prev_close

        # Fallback to history if still None
        if regular_price is None:
            hist = ticker.history(period='5d')
            if not hist.empty:
                regular_price = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev_close = float(hist['Close'].iloc[-2])

        if regular_price is None:
            return None

        result = {
            'symbol': ticker_symbol,
            'shortName': info.get('shortName', ticker_symbol),
            'longName': info.get('longName', info.get('shortName', ticker_symbol)),
            'exchange': info.get('exchange', 'N/A'),
            'currency': info.get('currency', 'USD'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'website': info.get('website', ''),
            'longBusinessSummary': info.get('longBusinessSummary', ''),
            'country': info.get('country', 'N/A'),
            'fullTimeEmployees': info.get('fullTimeEmployees', 'N/A'),

            # Price data
            'regularMarketPrice': round(float(regular_price), 2) if regular_price else None,
            'previousClose': round(float(prev_close), 2) if prev_close else None,
            'open': round(float(info['open']), 2) if info.get('open') else (round(float(info['regularMarketOpen']), 2) if info.get('regularMarketOpen') else None),
            'dayHigh': round(float(info['dayHigh']), 2) if info.get('dayHigh') else (round(float(info['regularMarketDayHigh']), 2) if info.get('regularMarketDayHigh') else None),
            'dayLow': round(float(info['dayLow']), 2) if info.get('dayLow') else (round(float(info['regularMarketDayLow']), 2) if info.get('regularMarketDayLow') else None),
            'volume': int(info['volume']) if info.get('volume') else (int(info['regularMarketVolume']) if info.get('regularMarketVolume') else None),
            'averageVolume': int(info['averageVolume']) if info.get('averageVolume') else None,
            'fiftyTwoWeekHigh': round(float(info['fiftyTwoWeekHigh']), 2) if info.get('fiftyTwoWeekHigh') else None,
            'fiftyTwoWeekLow': round(float(info['fiftyTwoWeekLow']), 2) if info.get('fiftyTwoWeekLow') else None,

            # Fundamental data
            'marketCap': int(info['marketCap']) if info.get('marketCap') else None,
            'trailingPE': round(float(info['trailingPE']), 2) if info.get('trailingPE') else None,
            'forwardPE': round(float(info['forwardPE']), 2) if info.get('forwardPE') else None,
            'trailingEps': round(float(info['trailingEps']), 2) if info.get('trailingEps') else None,
            'forwardEps': round(float(info['forwardEps']), 2) if info.get('forwardEps') else None,
            'priceToBook': round(float(info['priceToBook']), 2) if info.get('priceToBook') else None,
            'priceToSalesTrailing12Months': round(float(info['priceToSalesTrailing12Months']), 2) if info.get('priceToSalesTrailing12Months') else None,
            'enterpriseValue': int(info['enterpriseValue']) if info.get('enterpriseValue') else None,
            'revenue': int(info['totalRevenue']) if info.get('totalRevenue') else None,
            'netIncome': int(info['netIncomeToCommon']) if info.get('netIncomeToCommon') else None,
            'profitMargins': round(float(info['profitMargins']), 4) if info.get('profitMargins') else None,
            'operatingMargins': round(float(info['operatingMargins']), 4) if info.get('operatingMargins') else None,
            'returnOnEquity': round(float(info['returnOnEquity']), 4) if info.get('returnOnEquity') else None,
            'debtToEquity': round(float(info['debtToEquity']), 2) if info.get('debtToEquity') else None,
            'freeCashflow': int(info['freeCashflow']) if info.get('freeCashflow') else None,
            'dividendYield': round(float(info['dividendYield']), 4) if info.get('dividendYield') else None,
            'dividendRate': round(float(info['dividendRate']), 2) if info.get('dividendRate') else None,
            'beta': round(float(info['beta']), 2) if info.get('beta') else None,
            'bookValue': round(float(info['bookValue']), 2) if info.get('bookValue') else None,
            'earningsGrowth': round(float(info['earningsGrowth']), 4) if info.get('earningsGrowth') else None,
            'revenueGrowth': round(float(info['revenueGrowth']), 4) if info.get('revenueGrowth') else None,

            # Analyst data
            'targetMeanPrice': round(float(info['targetMeanPrice']), 2) if info.get('targetMeanPrice') else None,
            'targetHighPrice': round(float(info['targetHighPrice']), 2) if info.get('targetHighPrice') else None,
            'targetLowPrice': round(float(info['targetLowPrice']), 2) if info.get('targetLowPrice') else None,
            'recommendationKey': info.get('recommendationKey', 'N/A'),
            'numberOfAnalystOpinions': info.get('numberOfAnalystOpinions'),

            # Real market data metadata
            'marketDataTimestamp': _get_timestamp_str(),
            'isRealTime': False,
            'dataSource': 'Yahoo Finance (yfinance)',
            'dataNote': 'Quotes have standard ~15-minute exchange delay or represent end-of-day market close.'
        }

        # Calculate change
        if result['regularMarketPrice'] is not None and result['previousClose'] is not None and result['previousClose'] > 0:
            result['change'] = round(result['regularMarketPrice'] - result['previousClose'], 2)
            result['changePercent'] = round(((result['regularMarketPrice'] - result['previousClose']) / result['previousClose']) * 100, 2)
        else:
            result['change'] = None
            result['changePercent'] = None

        cache_set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f'Error fetching info for {ticker_symbol}: {e}')
        return None


def get_stock_price(ticker_symbol):
    """Fetch latest price data only."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'price_{ticker_symbol}'
    cached = cache_get(cache_key, ttl=60)  # Short TTL for price
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)

        current = None
        prev_close = None

        # 1. Try fast_info first (fastest and cleanest)
        try:
            fast = getattr(ticker, 'fast_info', None)
            if fast:
                current = getattr(fast, 'last_price', None)
                prev_close = getattr(fast, 'previous_close', None)
        except Exception:
            pass

        # 2. Fallback to info
        if current is None:
            try:
                info = ticker.info or {}
                current = info.get('regularMarketPrice') or info.get('currentPrice')
                prev_close = info.get('previousClose')
            except Exception:
                info = {}
        else:
            info = {}

        # 3. Fallback to 5-day history
        if current is None:
            hist = ticker.history(period='5d')
            if not hist.empty:
                current = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev_close = float(hist['Close'].iloc[-2])

        if current is None:
            return None

        current = float(current)
        prev_close = float(prev_close) if prev_close is not None else None

        change = None
        change_pct = None
        if current is not None and prev_close is not None and prev_close > 0:
            change = round(current - prev_close, 2)
            change_pct = round(((current - prev_close) / prev_close) * 100, 2)

        result = {
            'symbol': ticker_symbol,
            'price': round(current, 2),
            'previousClose': round(prev_close, 2) if prev_close else None,
            'change': change,
            'changePercent': change_pct,
            'open': round(float(info['open']), 2) if info.get('open') else None,
            'dayHigh': round(float(info['dayHigh']), 2) if info.get('dayHigh') else None,
            'dayLow': round(float(info['dayLow']), 2) if info.get('dayLow') else None,
            'volume': int(info['volume']) if info.get('volume') else None,
            'currency': info.get('currency', 'USD'),
            'marketDataTimestamp': _get_timestamp_str(),
            'isRealTime': False,
            'dataSource': 'Yahoo Finance (yfinance)'
        }

        cache_set(cache_key, result, ttl=60)
        return result

    except Exception as e:
        logger.error(f'Error fetching price for {ticker_symbol}: {e}')
        return None


def get_history(ticker_symbol, period='1y', interval='1d'):
    """Fetch real historical OHLCV data with Adjusted Close."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'history_{ticker_symbol}_{period}_{interval}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)
        # Fetch data with auto_adjust=False to keep Adjusted Close separate where available
        hist = ticker.history(period=period, interval=interval, auto_adjust=False)

        if hist.empty:
            # Fallback to default history call if auto_adjust=False returned empty
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                return []

        # Reset index to get date as a column
        hist = hist.reset_index()

        records = []
        for _, row in hist.iterrows():
            date_val = row.get('Date') if 'Date' in row else row.get('Datetime')
            if date_val is not None:
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)[:10]
            else:
                continue

            open_val = float(row['Open']) if pd.notna(row.get('Open')) else None
            high_val = float(row['High']) if pd.notna(row.get('High')) else None
            low_val = float(row['Low']) if pd.notna(row.get('Low')) else None
            close_val = float(row['Close']) if pd.notna(row.get('Close')) else None
            
            # Adjusted Close where available
            adj_close_raw = row.get('Adj Close') if 'Adj Close' in row else close_val
            adj_close_val = float(adj_close_raw) if pd.notna(adj_close_raw) else close_val

            records.append({
                'date': date_str,
                'open': round(open_val, 2) if open_val is not None else None,
                'high': round(high_val, 2) if high_val is not None else None,
                'low': round(low_val, 2) if low_val is not None else None,
                'close': round(close_val, 2) if close_val is not None else None,
                'adjClose': round(adj_close_val, 2) if adj_close_val is not None else None,
                'volume': int(row['Volume']) if pd.notna(row.get('Volume')) else 0,
            })

        cache_set(cache_key, records)
        return records

    except Exception as e:
        logger.error(f'Error fetching history for {ticker_symbol}: {e}')
        return []


def get_financials(ticker_symbol, stmt_type='income', freq='annual'):
    """Fetch financial statements."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'financials_{ticker_symbol}_{stmt_type}_{freq}'
    cached = cache_get(cache_key, ttl=3600)  # Cache for 1 hour
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)

        if stmt_type == 'income':
            df = ticker.quarterly_financials if freq == 'quarterly' else ticker.financials
        elif stmt_type == 'balance':
            df = ticker.quarterly_balance_sheet if freq == 'quarterly' else ticker.balance_sheet
        elif stmt_type == 'cashflow':
            df = ticker.quarterly_cashflow if freq == 'quarterly' else ticker.cashflow
        else:
            return None

        if df is None or df.empty:
            return None

        # Convert DataFrame to JSON-friendly format
        result = {
            'columns': [str(col.date()) if hasattr(col, 'date') else str(col)[:10] for col in df.columns],
            'rows': []
        }

        for idx, row in df.iterrows():
            row_data = {
                'metric': str(idx),
                'values': []
            }
            for val in row:
                if pd.isna(val):
                    row_data['values'].append(None)
                else:
                    row_data['values'].append(float(val))
            result['rows'].append(row_data)

        cache_set(cache_key, result, ttl=3600)
        return result

    except Exception as e:
        logger.error(f'Error fetching financials for {ticker_symbol}: {e}')
        return None


def get_recommendations(ticker_symbol):
    """Fetch analyst recommendations."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'recommendations_{ticker_symbol}'
    cached = cache_get(cache_key, ttl=3600)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)
        recs = ticker.recommendations

        if recs is None or recs.empty:
            return []

        recs = recs.tail(20).reset_index()
        records = []
        for _, row in recs.iterrows():
            record = {}
            for col in recs.columns:
                val = row[col]
                if pd.isna(val):
                    record[col] = None
                elif hasattr(val, 'isoformat'):
                    record[col] = val.isoformat()
                else:
                    record[col] = str(val)
            records.append(record)

        cache_set(cache_key, records, ttl=3600)
        return records

    except Exception as e:
        logger.error(f'Error fetching recommendations for {ticker_symbol}: {e}')
        return []


def get_news(ticker_symbol):
    """Fetch news articles for a ticker."""
    ticker_symbol = ticker_symbol.strip().upper()
    cache_key = f'news_{ticker_symbol}'
    cached = cache_get(cache_key, ttl=600)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news

        if not news:
            return []

        articles = []
        for item in news[:15]:
            article = {
                'title': item.get('title', ''),
                'publisher': item.get('publisher', 'Unknown'),
                'link': item.get('link', ''),
                'publishTime': item.get('providerPublishTime', ''),
                'type': item.get('type', ''),
            }
            if article['publishTime'] and isinstance(article['publishTime'], (int, float)):
                try:
                    article['publishTime'] = datetime.fromtimestamp(article['publishTime'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                except Exception:
                    article['publishTime'] = ''
            articles.append(article)

        cache_set(cache_key, articles, ttl=600)
        return articles

    except Exception as e:
        logger.error(f'Error fetching news for {ticker_symbol}: {e}')
        return []


def get_market_overview():
    """Fetch major market indices data with sparkline histories."""
    cache_key = 'market_overview'
    cached = cache_get(cache_key, ttl=120)
    if cached is not None:
        return cached

    indices = {
        '^GSPC': {'name': 'S&P 500', 'region': 'US'},
        '^IXIC': {'name': 'NASDAQ', 'region': 'US'},
        '^DJI': {'name': 'Dow Jones', 'region': 'US'},
        '^NSEI': {'name': 'NIFTY 50', 'region': 'India'},
        '^BSESN': {'name': 'SENSEX', 'region': 'India'},
    }

    results = []
    for symbol, meta in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')

            current = None
            prev = None

            if not hist.empty:
                current = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev = float(hist['Close'].iloc[-2])

            change = None
            change_pct = None
            if current is not None and prev is not None and prev > 0:
                change = round(current - prev, 2)
                change_pct = round(((current - prev) / prev) * 100, 2)

            chart_data = []
            if not hist.empty:
                for _, row in hist.iterrows():
                    if pd.notna(row['Close']):
                        chart_data.append(round(float(row['Close']), 2))

            results.append({
                'symbol': symbol,
                'name': meta['name'],
                'region': meta['region'],
                'price': round(current, 2) if current else None,
                'change': change,
                'changePercent': change_pct,
                'chartData': chart_data,
                'isRealTime': False,
                'timestamp': _get_timestamp_str()
            })

        except Exception as e:
            logger.error(f'Error fetching index {symbol}: {e}')
            results.append({
                'symbol': symbol,
                'name': meta['name'],
                'region': meta['region'],
                'price': None,
                'change': None,
                'changePercent': None,
                'chartData': [],
                'isRealTime': False,
                'timestamp': _get_timestamp_str()
            })

    cache_set(cache_key, results, ttl=120)
    return results


def search_ticker(query):
    """Validate and search for a ticker symbol using real market data."""
    query = query.strip().upper()
    cache_key = f'search_{query}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(query)
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass

        regular_price = info.get('regularMarketPrice') or info.get('currentPrice')
        if regular_price is None:
            hist = ticker.history(period='5d')
            if not hist.empty:
                regular_price = float(hist['Close'].iloc[-1])

        if regular_price is None:
            return None

        result = {
            'symbol': query,
            'shortName': info.get('shortName', query),
            'longName': info.get('longName', info.get('shortName', query)),
            'exchange': info.get('exchange', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'currency': info.get('currency', 'USD'),
            'regularMarketPrice': round(float(regular_price), 2),
            'marketDataTimestamp': _get_timestamp_str(),
            'isRealTime': False
        }

        cache_set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f'Error searching for {query}: {e}')
        return None
