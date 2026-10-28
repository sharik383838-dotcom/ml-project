"""
Authentication, Watchlist, Portfolio, Search History, and Prediction History routes.
Standardized JSON responses, session authentication, and database persistence.
"""

import logging
import hashlib
import secrets
from flask import Blueprint, request, session
from backend.database import get_db, get_prediction_records, get_recent_searches
from backend.services import yahoo_service
from backend.utils.json_response import api_response, api_error
from backend.utils.validators import (
    validate_username, validate_password, validate_ticker,
    validate_positive_number, validate_date
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def _hash_password(password):
    """Hash a password with a salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'{salt}:{hashed}'


def _verify_password(stored_hash, password):
    """Verify a password against a stored hash."""
    try:
        salt, hashed = stored_hash.split(':')
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False


def _ensure_guest_user():
    """Create a stable guest record so anonymous portfolio/watchlist actions keep working."""
    user_id = session.get('user_id')
    if user_id:
        return user_id

    guest_username = session.get('username') or f'guest_{secrets.token_hex(4)}'
    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE username = ?', (guest_username,)).fetchone()
    if existing:
        session['user_id'] = existing['id']
        session['username'] = guest_username
        return existing['id']

    password_hash = _hash_password(secrets.token_hex(16))
    cursor = db.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (guest_username, password_hash)
    )
    db.commit()
    session['user_id'] = cursor.lastrowid
    session['username'] = guest_username
    return cursor.lastrowid


def _get_user_id():
    """Get the current user ID, defaulting to an anonymous guest when no login is used."""
    return session.get('user_id') or _ensure_guest_user()


def _login_required(f):
    """Compatibility decorator: keep public dashboard features available without login."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        _get_user_id()
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/api/auth/status')
def auth_status():
    """Return the current session's authentication status."""
    user_id = _get_user_id()
    return api_response({
        'authenticated': bool(session.get('authenticated')),
        'username': session.get('username'),
        'user_id': user_id
    })


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Register a user and start an authenticated session."""
    data = request.get_json(silent=True) or {}
    username = validate_username(data.get('username'))
    password = validate_password(data.get('password'))
    if not username or not password:
        return api_error('Enter a valid username and a password of at least 6 characters.', 400)

    db = get_db()
    if db.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
        return api_error('Username already taken.', 409)

    cursor = db.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, _hash_password(password))
    )
    db.commit()
    session.clear()
    session['user_id'] = cursor.lastrowid
    session['username'] = username
    session['authenticated'] = True
    return api_response({'message': 'Account created.', 'username': username})


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate a user and start a session."""
    data = request.get_json(silent=True) or {}
    username = validate_username(data.get('username'))
    password = data.get('password')
    if not username or not password:
        return api_error('Invalid username or password.', 401)

    db = get_db()
    user = db.execute(
        'SELECT id, username, password_hash FROM users WHERE username = ?',
        (username,)
    ).fetchone()
    if not user or not _verify_password(user['password_hash'], password):
        return api_error('Invalid username or password.', 401)

    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['authenticated'] = True
    return api_response({'message': 'Signed in.', 'username': user['username']})


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """End the current session."""
    session.clear()
    return api_response({'message': 'Signed out.'})


@auth_bp.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
@_login_required
def manage_watchlist():
    """List, add, or remove a user's watched tickers."""
    db = get_db()
    user_id = _get_user_id()

    if request.method == 'GET':
        rows = db.execute(
            'SELECT id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC',
            (user_id,)
        ).fetchall()
        return api_response({'watchlist': [dict(row) for row in rows]})

    data = request.get_json(silent=True) or {}
    ticker = validate_ticker(data.get('ticker'))
    if not ticker:
        return api_error('Invalid ticker symbol.', 400)

    if request.method == 'POST':
        db.execute('INSERT OR IGNORE INTO watchlist (user_id, ticker) VALUES (?, ?)', (user_id, ticker))
        db.commit()
        return api_response({'message': f'{ticker} added to watchlist.'})

    db.execute('DELETE FROM watchlist WHERE user_id = ? AND ticker = ?', (user_id, ticker))
    db.commit()
    return api_response({'message': f'{ticker} removed from watchlist.'})


@auth_bp.route('/api/portfolio', methods=['GET', 'POST', 'DELETE'])
@_login_required
def manage_portfolio():
    """List, add, or remove a user's portfolio holdings."""
    db = get_db()
    user_id = _get_user_id()

    if request.method == 'GET':
        rows = db.execute(
            'SELECT id, ticker, quantity, purchase_price, purchase_date, added_at '
            'FROM portfolio WHERE user_id = ? ORDER BY added_at DESC',
            (user_id,)
        ).fetchall()
        return api_response({'portfolio': [dict(row) for row in rows]})

    data = request.get_json(silent=True) or {}
    if request.method == 'POST':
        ticker = validate_ticker(data.get('ticker'))
        quantity = validate_positive_number(data.get('quantity'))
        purchase_price = validate_positive_number(data.get('purchase_price'))
        purchase_date = validate_date(data.get('purchase_date'))
        if not ticker or not quantity or not purchase_price:
            return api_error('Provide a valid ticker, quantity, and purchase price.', 400)
        cursor = db.execute(
            'INSERT INTO portfolio (user_id, ticker, quantity, purchase_price, purchase_date) '
            'VALUES (?, ?, ?, ?, ?)',
            (user_id, ticker, quantity, purchase_price, purchase_date)
        )
        db.commit()
        return api_response({'id': cursor.lastrowid, 'message': f'{ticker} holding added.'})

    holding_id = data.get('id')
    if not isinstance(holding_id, int):
        return api_error('Provide a valid holding id.', 400)
    db.execute('DELETE FROM portfolio WHERE id = ? AND user_id = ?', (holding_id, user_id))
    db.commit()
    return api_response({'message': 'Holding removed.'})


# ─── Watchlist Routes ───

# ─── Search & Prediction History Routes ───

@auth_bp.route('/api/search/history', methods=['GET'])
def get_user_search_history():
    """Get recent searches from database."""
    user_id = _get_user_id()
    searches = get_recent_searches(user_id=user_id, limit=10)
    return api_response({'searches': searches})


@auth_bp.route('/api/prediction/history', methods=['GET'])
def get_user_prediction_history():
    """Get recent ML prediction history from database."""
    user_id = _get_user_id()
    ticker = request.args.get('ticker')
    records = get_prediction_records(user_id=user_id, ticker=ticker, limit=15)
    return api_response({'predictions': records})


# ─── Favorites Routes ───

@auth_bp.route('/api/favorites', methods=['GET'])
@_login_required
def get_favorites():
    """Get favorite stocks for user."""
    user_id = _get_user_id()
    db = get_db()
    rows = db.execute('SELECT ticker, added_at FROM favorite_stocks WHERE user_id = ? ORDER BY added_at DESC', (user_id,)).fetchall()
    return api_response({'favorites': [dict(r) for r in rows]})


@auth_bp.route('/api/favorites', methods=['POST'])
@_login_required
def add_favorite():
    """Add favorite stock for user."""
    data = request.get_json() or {}
    ticker = validate_ticker(data.get('ticker'))
    if not ticker:
        return api_error('Invalid ticker symbol.', 400)

    user_id = _get_user_id()
    db = get_db()
    try:
        db.execute('INSERT OR IGNORE INTO favorite_stocks (user_id, ticker) VALUES (?, ?)', (user_id, ticker))
        db.commit()
        return api_response({'message': f'{ticker} added to favorites.'})
    except Exception as e:
        logger.error(f'Error adding favorite: {e}')
        return api_error('Failed to add favorite.', 500)


@auth_bp.route('/api/favorites', methods=['DELETE'])
@_login_required
def remove_favorite():
    """Remove favorite stock for user."""
    data = request.get_json() or {}
    ticker = validate_ticker(data.get('ticker'))
    if not ticker:
        return api_error('Invalid ticker symbol.', 400)

    user_id = _get_user_id()
    db = get_db()
    try:
        db.execute('DELETE FROM favorite_stocks WHERE user_id = ? AND ticker = ?', (user_id, ticker))
        db.commit()
        return api_response({'message': f'{ticker} removed from favorites.'})
    except Exception as e:
        logger.error(f'Error removing favorite: {e}')
        return api_error('Failed to remove favorite.', 500)
