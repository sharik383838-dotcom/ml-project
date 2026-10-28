"""
Database module for StockLens.
Handles SQLite connection management, connection pooling / reuse per request,
timeout handling, error handling, and schema initialization.
"""

import os
import sqlite3
import logging
from flask import g, current_app, has_app_context

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.getenv('DATABASE_TIMEOUT', '15.0'))


def _get_default_db_path():
    """Determine absolute path to the SQLite database file."""
    db_env_path = os.getenv('DATABASE_PATH')
    if db_env_path:
        if os.path.isabs(db_env_path):
            return db_env_path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(base_dir, db_env_path))
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'stocklens.db')


def get_db():
    """
    Get a database connection for the current request context.
    Reuses existing connection in `g` or establishes a new one with timeout handling.
    Works seamlessly both within and outside Flask application context.
    """
    if has_app_context():
        if 'db' not in g:
            db_path = current_app.config.get('DATABASE') or _get_default_db_path()
            timeout = float(current_app.config.get('DATABASE_TIMEOUT', DEFAULT_TIMEOUT))
            try:
                conn = sqlite3.connect(
                    db_path,
                    timeout=timeout,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA foreign_keys=ON')
                conn.execute('PRAGMA busy_timeout = 5000')
                g.db = conn
            except sqlite3.Error as e:
                logger.error(f'Database connection failure to "{db_path}": {e}')
                raise ConnectionError(f'Failed to connect to database: {e}') from e
        return g.db
    else:
        db_path = _get_default_db_path()
        conn = sqlite3.connect(db_path, timeout=DEFAULT_TIMEOUT, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn


def close_db(exception=None):
    """Close database connection at the end of the request context."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except sqlite3.Error as e:
            logger.warning(f'Error closing database connection: {e}')


def check_db_connection():
    """
    Health check for database connectivity.
    Returns dict with connection status, database engine, and metrics.
    """
    try:
        db = get_db()
        cursor = db.execute('SELECT 1 AS alive')
        row = cursor.fetchone()
        is_alive = bool(row and row['alive'] == 1)

        # Get table counts
        counts = {}
        for table in ['users', 'prediction_history', 'search_history']:
            try:
                c = db.execute(f'SELECT COUNT(*) AS cnt FROM {table}').fetchone()
                counts[table] = c['cnt'] if c else 0
            except sqlite3.Error:
                counts[table] = 0

        return {
            'status': 'connected' if is_alive else 'disconnected',
            'engine': 'SQLite',
            'databasePath': current_app.config.get('DATABASE', 'stocklens.db'),
            'tables': counts,
            'isHealthy': is_alive
        }
    except Exception as e:
        logger.error(f'Database health check failed: {e}')
        return {
            'status': 'error',
            'engine': 'SQLite',
            'error': str(e),
            'isHealthy': False
        }


def init_db(app):
    """Initialize the database schema."""
    db_path = app.config.get('DATABASE')
    timeout = float(app.config.get('DATABASE_TIMEOUT', DEFAULT_TIMEOUT))

    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path, timeout=timeout) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticker TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS favorite_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, ticker)
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, ticker)
                );

                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    purchase_date TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS prediction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticker TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    predicted_price REAL NOT NULL,
                    predicted_change REAL,
                    predicted_change_percent REAL,
                    mae REAL,
                    rmse REAL,
                    directional_accuracy REAL,
                    model_name TEXT DEFAULT 'RandomForestRegressor',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS stock_analysis_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT UNIQUE NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_search_ticker ON search_history(ticker);
                CREATE INDEX IF NOT EXISTS idx_pred_ticker ON prediction_history(ticker);
                CREATE INDEX IF NOT EXISTS idx_pred_user ON prediction_history(user_id);
            ''')
            logger.info('Database initialized successfully with all tables.')
    except Exception as e:
        logger.error(f'Database initialization error: {e}')
        raise


# ─── Helper Query Functions ───

def record_search(ticker, user_id=None):
    """Record a ticker search in the search history."""
    try:
        db = get_db()
        db.execute(
            'INSERT INTO search_history (user_id, ticker) VALUES (?, ?)',
            (user_id, ticker.upper())
        )
        db.commit()
    except Exception as e:
        logger.warning(f'Failed to record search history: {e}')


def get_recent_searches(user_id=None, limit=10):
    """Retrieve recent searches."""
    try:
        db = get_db()
        if user_id:
            rows = db.execute(
                '''SELECT ticker, MAX(created_at) as last_searched, COUNT(*) as count 
                   FROM search_history 
                   WHERE user_id = ? 
                   GROUP BY ticker 
                   ORDER BY last_searched DESC LIMIT ?''',
                (user_id, limit)
            ).fetchall()
        else:
            rows = db.execute(
                '''SELECT ticker, MAX(created_at) as last_searched, COUNT(*) as count 
                   FROM search_history 
                   GROUP BY ticker 
                   ORDER BY last_searched DESC LIMIT ?''',
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f'Failed to get search history: {e}')
        return []


def save_prediction_record(ticker, current_price, predicted_price, predicted_change,
                           predicted_change_pct, mae, rmse, directional_accuracy,
                           model_name='RandomForestRegressor', user_id=None):
    """Save a stock price prediction record."""
    try:
        db = get_db()
        cursor = db.execute(
            '''INSERT INTO prediction_history 
               (user_id, ticker, current_price, predicted_price, predicted_change,
                predicted_change_percent, mae, rmse, directional_accuracy, model_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, ticker.upper(), current_price, predicted_price, predicted_change,
             predicted_change_pct, mae, rmse, directional_accuracy, model_name)
        )
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f'Failed to save prediction record: {e}')
        return None


def get_prediction_records(user_id=None, ticker=None, limit=15):
    """Retrieve prediction history records."""
    try:
        db = get_db()
        query = 'SELECT * FROM prediction_history WHERE 1=1'
        params = []
        if ticker:
            query += ' AND ticker = ?'
            params.append(ticker.upper())
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        rows = db.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f'Failed to fetch prediction history: {e}')
        return []
