"""
Input validation utilities for StockLens.
"""

import re
import html


def validate_ticker(ticker):
    """
    Validate a stock ticker symbol.
    Allows letters, digits, dots, hyphens, and carets (for indices like ^GSPC).
    Returns sanitized uppercase ticker or None if invalid.
    """
    if not ticker or not isinstance(ticker, str):
        return None
    
    ticker = ticker.strip().upper()
    
    # Allow: A-Z, 0-9, dot (for .NS, .KS etc), hyphen, caret (for indices)
    if not re.match(r'^[\^A-Z0-9.\-]{1,20}$', ticker):
        return None
    
    return ticker


def validate_period(period):
    """Validate a history period string."""
    valid_periods = {'1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'}
    if period and period.lower() in valid_periods:
        return period.lower()
    return '1y'  # default


def validate_interval(interval):
    """Validate a history interval string."""
    valid_intervals = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'}
    if interval and interval.lower() in valid_intervals:
        return interval.lower()
    return '1d'  # default


def validate_stmt_type(stmt_type):
    """Validate financial statement type."""
    valid = {'income', 'balance', 'cashflow'}
    if stmt_type and stmt_type.lower() in valid:
        return stmt_type.lower()
    return 'income'


def validate_frequency(freq):
    """Validate annual/quarterly frequency."""
    valid = {'annual', 'quarterly'}
    if freq and freq.lower() in valid:
        return freq.lower()
    return 'annual'


def sanitize_string(s, max_length=200):
    """Sanitize and escape a string input."""
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()[:max_length]
    return html.escape(s)


def validate_username(username):
    """Validate username: 3-30 chars, alphanumeric + underscore."""
    if not username or not isinstance(username, str):
        return None
    username = username.strip()
    if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
        return None
    return username


def validate_password(password):
    """Validate password: minimum 6 characters."""
    if not password or not isinstance(password, str):
        return None
    if len(password) < 6:
        return None
    return password


def validate_positive_number(value):
    """Validate and return a positive number."""
    try:
        num = float(value)
        if num > 0:
            return num
        return None
    except (TypeError, ValueError):
        return None


def validate_date(date_str):
    """Validate a date string in YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        return None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    return None
