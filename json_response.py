"""
JSON Response and Serialization Utilities for StockLens.
Ensures standard JSON API structures and safe serialization of
NaN, Infinity, numpy types, and pandas structures.
"""

import math
import json
import logging
from datetime import date, datetime
from flask import Response

logger = logging.getLogger(__name__)


def clean_for_json(obj):
    """
    Recursively clean an object to make it strictly valid JSON compliant.
    Converts:
      - float('nan'), float('inf'), float('-inf') -> None (null)
      - numpy scalars -> native Python types (int, float, bool)
      - numpy arrays / pandas Series -> Python lists
      - pandas DataFrames -> list of dicts
      - dates / datetimes / Timestamps -> ISO 8601 strings
    Never calls pd.isna on multi-element collections.
    """
    if obj is None:
        return None

    # Handle standard primitives
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # Handle lists / tuples / sets
    if isinstance(obj, (list, tuple, set)):
        return [clean_for_json(x) for x in obj]

    # Handle dicts
    if isinstance(obj, dict):
        return {str(k): clean_for_json(v) for k, v in obj.items()}

    # Handle dates and datetimes
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Handle numpy types if numpy is available
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return [clean_for_json(x) for x in obj.tolist()]
        if isinstance(obj, (np.floating, float)):
            f_val = float(obj)
            return None if math.isnan(f_val) or math.isinf(f_val) else f_val
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
    except ImportError:
        pass

    # Handle pandas types if pandas is available
    try:
        import pandas as pd
        if isinstance(obj, pd.Series):
            return [clean_for_json(x) for x in obj.tolist()]
        if isinstance(obj, pd.DataFrame):
            return [clean_for_json(row) for row in obj.to_dict(orient='records')]
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
    except ImportError:
        pass

    # Fallback to string or dict representation if possible
    if hasattr(obj, 'to_dict'):
        try:
            return clean_for_json(obj.to_dict())
        except Exception:
            pass

    return str(obj)


def api_response(data=None, status=200, headers=None):
    """
    Create a standardized success JSON response:
    {
        "success": true,
        "data": { ... },
        "error": null
    }
    """
    cleaned = clean_for_json(data) if data is not None else {}
    payload = {
        'success': True,
        'data': cleaned,
        'error': None
    }
    json_bytes = json.dumps(payload, allow_nan=False)
    
    resp = Response(
        response=json_bytes,
        status=status,
        mimetype='application/json'
    )
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp


def api_error(message, status=400, data=None):
    """
    Create a standardized error JSON response:
    {
        "success": false,
        "data": null,
        "error": "Clear error message"
    }
    """
    payload = {
        'success': False,
        'data': clean_for_json(data) if data is not None else None,
        'error': str(message) if message else 'An unknown error occurred.'
    }
    json_bytes = json.dumps(payload, allow_nan=False)

    resp = Response(
        response=json_bytes,
        status=status,
        mimetype='application/json'
    )
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    return resp
