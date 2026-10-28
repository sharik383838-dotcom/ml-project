"""
In-memory TTL cache for StockLens.
Simple dict-based cache with expiry timestamps.
"""

import time
import os
import threading
import logging

logger = logging.getLogger(__name__)

_cache = {}
_lock = threading.Lock()

DEFAULT_TTL = int(os.getenv('DATA_CACHE_SECONDS', 300))


def cache_get(key, ttl=None):
    """Get a value from cache if it exists and hasn't expired."""
    with _lock:
        if key in _cache:
            entry = _cache[key]
            effective_ttl = ttl or entry.get('ttl', DEFAULT_TTL)
            if time.time() - entry['timestamp'] < effective_ttl:
                return entry['value']
            else:
                del _cache[key]
    return None


def cache_set(key, value, ttl=None):
    """Store a value in cache with a TTL."""
    with _lock:
        _cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl or DEFAULT_TTL
        }


def cache_clear(key=None):
    """Clear one or all cache entries."""
    with _lock:
        if key:
            _cache.pop(key, None)
        else:
            _cache.clear()
    logger.info(f'Cache cleared: {"all" if key is None else key}')


def cache_stats():
    """Get cache statistics."""
    with _lock:
        total = len(_cache)
        valid = 0
        now = time.time()
        for entry in _cache.values():
            if now - entry['timestamp'] < entry.get('ttl', DEFAULT_TTL):
                valid += 1
        return {'total_entries': total, 'valid_entries': valid, 'expired_entries': total - valid}
