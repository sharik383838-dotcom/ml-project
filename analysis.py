"""
Analysis API routes for StockLens.
Standardized JSON responses for technical analysis and multi-stock comparisons.
"""

import logging
import numpy as np
from flask import Blueprint, request
from backend.services import yahoo_service
from backend.services.analysis_service import run_full_analysis
from backend.utils.validators import validate_ticker
from backend.utils.json_response import api_response, api_error

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/stock/<ticker>/analysis')
def get_analysis(ticker):
    """Get technical analysis for a stock."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    # Fetch 1 year of daily data for analysis
    try:
        history = yahoo_service.get_history(validated, period='1y', interval='1d')
        if not history:
            return api_error(f'Insufficient data for analysis of "{validated}".', 404)

        result = run_full_analysis(history)
        if 'error' in result:
            return api_error(result['error'], 400)

        result['symbol'] = validated
        return api_response(result)
    except Exception as e:
        logger.error(f'Analysis error for {validated}: {e}')
        return api_error(f'Technical analysis failed for "{validated}": {str(e)}', 500)


@analysis_bp.route('/compare')
def compare_stocks():
    """Compare multiple stocks."""
    tickers_param = request.args.get('tickers', '')
    if not tickers_param:
        return api_error('Provide tickers as comma-separated values. Example: ?tickers=AAPL,MSFT,NVDA', 400)

    raw_tickers = [t.strip() for t in tickers_param.split(',') if t.strip()]

    if len(raw_tickers) < 2:
        return api_error('Please provide at least 2 tickers to compare.', 400)

    if len(raw_tickers) > 6:
        return api_error('Maximum 6 tickers can be compared at once.', 400)

    validated_tickers = []
    for t in raw_tickers:
        v = validate_ticker(t)
        if v:
            validated_tickers.append(v)

    if len(validated_tickers) < 2:
        return api_error('Not enough valid tickers for comparison.', 400)

    results = []
    for ticker in validated_tickers:
        try:
            info = yahoo_service.get_stock_info(ticker)
            if not info:
                results.append({'symbol': ticker, 'error': 'Data not available'})
                continue

            # Get 1Y history for performance calculation
            history = yahoo_service.get_history(ticker, period='1y', interval='1d')

            # Calculate returns
            return_1m = None
            return_1y = None
            volatility = None

            if history and len(history) > 0:
                closes = [h['close'] for h in history if h['close'] is not None]
                if closes:
                    current = closes[-1]
                    if len(closes) > 22:
                        return_1m = round(((current / closes[-22]) - 1) * 100, 2)
                    if len(closes) > 250:
                        return_1y = round(((current / closes[0]) - 1) * 100, 2)

                    # Calculate volatility
                    returns = []
                    for i in range(1, len(closes)):
                        returns.append((closes[i] / closes[i - 1]) - 1)
                    if returns:
                        volatility = round(float(np.std(returns) * np.sqrt(252) * 100), 2)

            compare_data = {
                'symbol': ticker,
                'shortName': info.get('shortName', ticker),
                'price': info.get('regularMarketPrice'),
                'change': info.get('change'),
                'changePercent': info.get('changePercent'),
                'marketCap': info.get('marketCap'),
                'trailingPE': info.get('trailingPE'),
                'trailingEps': info.get('trailingEps'),
                'revenue': info.get('revenue'),
                'profitMargins': info.get('profitMargins'),
                'dividendYield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'return_1m': return_1m,
                'return_1y': return_1y,
                'volatility': volatility,
                'currency': info.get('currency', 'USD'),
            }

            # Get normalized price history for chart
            if history:
                first_close = None
                for h in history:
                    if h['close'] is not None:
                        first_close = h['close']
                        break
                if first_close:
                    compare_data['chartData'] = {
                        'dates': [h['date'][:10] for h in history],
                        'normalized': [round(((h['close'] / first_close) - 1) * 100, 2) if h['close'] else None for h in history],
                        'prices': [h['close'] for h in history],
                    }

            results.append(compare_data)

        except Exception as e:
            logger.error(f'Error comparing {ticker}: {e}')
            results.append({'symbol': ticker, 'error': str(e)})

    return api_response({'tickers': validated_tickers, 'comparison': results})
