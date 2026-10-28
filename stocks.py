"""
Stock data API routes for StockLens.
Standardized JSON responses, input validation, real market data,
and machine-learning stock price predictions.
"""

import logging
from flask import Blueprint, request, session
from backend.services import yahoo_service
from backend.services.prediction_service import generate_stock_prediction
from backend.database import record_search, check_db_connection
from backend.utils.json_response import api_response, api_error
from backend.utils.validators import (
    validate_ticker, validate_period, validate_interval,
    validate_stmt_type, validate_frequency
)

logger = logging.getLogger(__name__)

stocks_bp = Blueprint('stocks', __name__)


@stocks_bp.route('/stock/<ticker>')
def get_stock(ticker):
    """Get comprehensive stock information."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol. Use formats like AAPL, MSFT, RELIANCE.NS, 005930.KS', 400)

    try:
        data = yahoo_service.get_stock_info(validated)
        if not data:
            return api_error(f'No market data found for ticker "{validated}". Please verify the symbol.', 404)

        return api_response(data)
    except Exception as e:
        logger.error(f'Error fetching stock info for {validated}: {e}')
        return api_error(f'Unable to fetch stock data for "{validated}".', 500)


@stocks_bp.route('/stock/<ticker>/price')
def get_stock_price(ticker):
    """Get latest price data only."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    try:
        data = yahoo_service.get_stock_price(validated)
        if not data:
            return api_error(f'Unable to fetch price for "{validated}".', 404)

        return api_response(data)
    except Exception as e:
        logger.error(f'Error fetching price for {validated}: {e}')
        return api_error(f'Unable to fetch price for "{validated}".', 500)


@stocks_bp.route('/stock/<ticker>/history')
def get_stock_history(ticker):
    """Get historical OHLCV data."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    period = validate_period(request.args.get('period', '1y'))
    interval = validate_interval(request.args.get('interval', '1d'))

    try:
        data = yahoo_service.get_history(validated, period=period, interval=interval)
        if not data:
            return api_error(f'No historical data available for "{validated}".', 404)

        return api_response({'symbol': validated, 'period': period, 'interval': interval, 'data': data})
    except Exception as e:
        logger.error(f'Error fetching history for {validated}: {e}')
        return api_error(f'Unable to fetch historical data for "{validated}".', 500)


@stocks_bp.route('/stock/<ticker>/prediction')
def get_stock_prediction(ticker):
    """
    Get machine-learning stock price prediction and performance metrics.
    GET /api/stock/<ticker>/prediction
    """
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    user_id = session.get('user_id')

    try:
        result = generate_stock_prediction(validated, user_id=user_id, force_refresh=force_refresh)
        return api_response(result)
    except ValueError as ve:
        logger.warning(f'Prediction validation error for {validated}: {ve}')
        return api_error(str(ve), 400)
    except Exception as e:
        logger.error(f'Prediction execution error for {validated}: {e}')
        return api_error(f'Prediction calculation failed for "{validated}": {str(e)}', 500)


@stocks_bp.route('/stock/<ticker>/metrics')
def get_stock_metrics(ticker):
    """
    Get model evaluation metrics only for a stock.
    GET /api/stock/<ticker>/metrics
    """
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    try:
        pred = generate_stock_prediction(validated, user_id=session.get('user_id'))
        metrics_payload = {
            'symbol': validated,
            'modelName': pred['modelName'],
            'metrics': pred['metrics'],
            'sampleCounts': pred['sampleCounts'],
            'uncertaintyInterval': pred['uncertaintyInterval'],
            'disclaimer': pred['disclaimer']
        }
        return api_response(metrics_payload)
    except Exception as e:
        logger.error(f'Error fetching metrics for {validated}: {e}')
        return api_error(f'Unable to calculate metrics for "{validated}": {str(e)}', 500)


@stocks_bp.route('/stock/<ticker>/financials')
def get_stock_financials(ticker):
    """Get financial statements."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    stmt_type = validate_stmt_type(request.args.get('type', 'income'))
    freq = validate_frequency(request.args.get('freq', 'annual'))

    try:
        data = yahoo_service.get_financials(validated, stmt_type=stmt_type, freq=freq)
        if not data:
            return api_error(f'Financial data not available for "{validated}".', 404)

        return api_response({'symbol': validated, 'type': stmt_type, 'frequency': freq, 'data': data})
    except Exception as e:
        logger.error(f'Error fetching financials for {validated}: {e}')
        return api_error(f'Unable to fetch financials for "{validated}".', 500)


@stocks_bp.route('/stock/<ticker>/news')
def get_stock_news(ticker):
    """Get news articles for a stock."""
    validated = validate_ticker(ticker)
    if not validated:
        return api_error('Invalid ticker symbol.', 400)

    try:
        data = yahoo_service.get_news(validated)
        return api_response({'symbol': validated, 'articles': data})
    except Exception as e:
        logger.error(f'Error fetching news for {validated}: {e}')
        return api_error(f'Unable to fetch news for "{validated}".', 500)


@stocks_bp.route('/search')
def search():
    """Search for a stock ticker."""
    query = request.args.get('q', '').strip()
    if not query:
        return api_error('Search query is required.', 400)

    validated = validate_ticker(query)
    if not validated:
        return api_error(f'Invalid ticker format: "{query}". Use formats like AAPL, RELIANCE.NS, 005930.KS', 400)

    try:
        # Record search history in the database
        record_search(validated, session.get('user_id'))

        data = yahoo_service.search_ticker(validated)
        if not data:
            return api_error(f'No results found for "{validated}". Please check the ticker symbol.', 404)

        return api_response(data)
    except Exception as e:
        logger.error(f'Error searching for {query}: {e}')
        return api_error(f'Search failed for "{query}".', 500)


@stocks_bp.route('/market/overview')
def market_overview():
    """Get major market indices overview."""
    try:
        data = yahoo_service.get_market_overview()
        return api_response({'indices': data})
    except Exception as e:
        logger.error(f'Error fetching market overview: {e}')
        return api_error('Unable to fetch market data. Please try again.', 500)


@stocks_bp.route('/status')
def system_status():
    """Check database and real market-data source status."""
    db_health = check_db_connection()
    return api_response({
        'database': db_health,
        'marketData': {
            'provider': 'Yahoo Finance (yfinance)',
            'status': 'operational',
            'isRealTime': False,
            'note': 'Standard 15-minute exchange delay on equities'
        }
    })
