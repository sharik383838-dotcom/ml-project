"""
Page routes for StockLens.
Serves HTML templates for frontend pages.
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """Homepage."""
    return render_template('index.html')


@pages_bp.route('/dashboard')
def dashboard():
    """Investor dashboard."""
    return render_template('dashboard.html')


@pages_bp.route('/stock/<ticker>')
def stock_detail(ticker):
    """Stock detail page."""
    return render_template('stock.html', ticker=ticker.upper())


@pages_bp.route('/compare')
def compare():
    """Stock comparison page."""
    return render_template('compare.html')
