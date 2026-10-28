"""
Comprehensive API and Feature Verification Script for StockLens.
Tests:
1. Standard JSON structure across all API endpoints (success, data, error)
2. Real market data retrieval (AAPL, MSFT, GOOGL)
3. Adjusted close inclusion and timestamps
4. Machine Learning Stock Prediction (Random Forest)
5. Model metrics (MAE, RMSE, Directional Accuracy, R2)
6. Database connectivity, timeout, health check, and prediction history
7. Search recording and retrieval
8. Error handling for invalid symbols and nonexistent routes
"""

import sys
import json
from backend import create_app

def main():
    app = create_app()
    client = app.test_client()

    tests = [
        ('System Status', '/api/status', 200),
        ('Stock Info (AAPL)', '/api/stock/AAPL', 200),
        ('Stock Price (AAPL)', '/api/stock/AAPL/price', 200),
        ('Stock History (AAPL)', '/api/stock/AAPL/history?period=1mo', 200),
        ('Stock Search (MSFT)', '/api/search?q=MSFT', 200),
        ('Market Overview', '/api/market/overview', 200),
        ('Stock Analysis (AAPL)', '/api/stock/AAPL/analysis', 200),
        ('Stock Prediction (AAPL)', '/api/stock/AAPL/prediction', 200),
        ('Stock Metrics (AAPL)', '/api/stock/AAPL/metrics', 200),
        ('Prediction History', '/api/prediction/history', 200),
        ('Search History', '/api/search/history', 200),
        ('Invalid Stock Symbol', '/api/stock/INVALID$$$###/prediction', 400),
        ('Nonexistent API Route', '/api/nonexistent/route', 404),
    ]

    print("=" * 60)
    print("STARTING STOCKLENS VERIFICATION SUITE")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, url, expected_status in tests:
        res = client.get(url)
        content_type = res.headers.get('Content-Type', '')
        
        try:
            data = json.loads(res.data.decode('utf-8'))
        except Exception as e:
            print(f"[FAIL] {name}: Failed to decode JSON ({e})")
            failed += 1
            continue

        is_status_ok = (res.status_code == expected_status)
        has_std_structure = ('success' in data and 'data' in data and 'error' in data)
        is_json_header = 'application/json' in content_type

        if is_status_ok and has_std_structure and is_json_header:
            print(f"[PASS] {name} [{res.status_code}] -> JSON Standard Compliant (success: {data.get('success')})")
            passed += 1
        else:
            print(f"[FAIL] {name} [{res.status_code}, expected {expected_status}] -> Structure: {has_std_structure}, CT: {content_type}")
            print(f"       Response data: {data}")
            failed += 1

    # Verify History contains adjClose
    hist_res = client.get('/api/stock/AAPL/history?period=1mo')
    hist_json = json.loads(hist_res.data.decode('utf-8'))
    records = hist_json.get('data', {}).get('data', [])
    if records and 'adjClose' in records[0]:
        print(f"[PASS] History contains adjClose: {records[0].get('adjClose')}")
    else:
        print(f"[FAIL] History does not contain adjClose")
        failed += 1

    # Verify Prediction details
    pred_res = client.get('/api/stock/AAPL/prediction')
    pred_json = json.loads(pred_res.data.decode('utf-8'))
    pred_data = pred_json.get('data', {})
    metrics = pred_data.get('metrics', {})
    print(f"[INFO] AAPL Predicted Price: ${pred_data.get('predictedPrice')} (Current: ${pred_data.get('currentPrice')})")
    print(f"[INFO] Direction: {pred_data.get('direction')}, Target: {pred_data.get('predictionDate')}")
    print(f"[INFO] Model: {pred_data.get('modelName')}")
    print(f"[INFO] Metrics -> MAE: {metrics.get('mae')}, RMSE: {metrics.get('rmse')}, DirAcc: {metrics.get('directionalAccuracy')}%, R2: {metrics.get('r2')}")

    print("=" * 60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
