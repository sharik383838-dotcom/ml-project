"""
Feature Engineering Module for Stock Price Prediction.
Extracts technical, momentum, volatility, and volume features from OHLCV data.
"""

import numpy as np
import pandas as pd


def compute_rsi(prices, period=14):
    """Compute Relative Strength Index (RSI)."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def build_prediction_features(ohlcv_df):
    """
    Build rich feature set for machine learning prediction from OHLCV data.
    
    Args:
        ohlcv_df: DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume']
    
    Returns:
        tuple: (features_df, feature_cols, target_col, latest_feature_row)
    """
    df = ohlcv_df.copy()
    
    # Ensure numeric types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['close', 'open', 'high', 'low', 'volume']).reset_index(drop=True)

    if len(df) < 50:
        raise ValueError(f"Insufficient data for feature engineering. Need >= 50 rows, got {len(df)}.")

    close = df['close']
    volume = df['volume']
    high = df['high']
    low = df['low']
    open_p = df['open']

    # 1. Price Returns
    df['ret_1d'] = close.pct_change(1)
    df['ret_5d'] = close.pct_change(5)
    df['ret_10d'] = close.pct_change(10)
    df['ret_21d'] = close.pct_change(21)
    df['open_close_ratio'] = (close - open_p) / (open_p + 1e-8)
    df['high_low_ratio'] = (high - low) / (close + 1e-8)

    # 2. Moving Averages & Moving Average Ratios
    df['sma_10'] = close.rolling(10).mean()
    df['sma_20'] = close.rolling(20).mean()
    df['sma_50'] = close.rolling(50).mean()
    df['ema_12'] = close.ewm(span=12, adjust=False).mean()
    df['ema_26'] = close.ewm(span=26, adjust=False).mean()

    df['ratio_sma10'] = (close / (df['sma_10'] + 1e-8)) - 1.0
    df['ratio_sma20'] = (close / (df['sma_20'] + 1e-8)) - 1.0
    df['ratio_sma50'] = (close / (df['sma_50'] + 1e-8)) - 1.0
    df['ratio_ema12'] = (close / (df['ema_12'] + 1e-8)) - 1.0
    df['ratio_ema26'] = (close / (df['ema_26'] + 1e-8)) - 1.0

    # 3. Momentum & Trend (RSI & MACD)
    df['rsi_14'] = compute_rsi(close, 14)
    macd_line = df['ema_12'] - df['ema_26']
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    df['macd_line'] = macd_line
    df['macd_signal'] = macd_signal
    df['macd_hist'] = macd_line - macd_signal

    # 4. Volatility (Rolling Std & Bollinger Bands)
    df['volatility_20d'] = df['ret_1d'].rolling(20).std() * np.sqrt(252)
    bb_std = close.rolling(20).std()
    df['bb_upper'] = df['sma_20'] + 2 * bb_std
    df['bb_lower'] = df['sma_20'] - 2 * bb_std
    df['bb_pct'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-8)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['sma_20'] + 1e-8)

    # 5. Volume Features
    df['vol_change_1d'] = volume.pct_change(1)
    df['vol_sma_20'] = volume.rolling(20).mean()
    df['vol_ratio'] = volume / (df['vol_sma_20'] + 1e-8)

    # 6. Target: Next Trading Day's Close Price
    # Notice: df.iloc[-1]['target_close'] will be NaN because tomorrow hasn't happened yet!
    # This row is our out-of-sample prediction input!
    df['target_close'] = close.shift(-1)

    feature_cols = [
        'close', 'open', 'high', 'low',
        'ret_1d', 'ret_5d', 'ret_10d', 'ret_21d',
        'open_close_ratio', 'high_low_ratio',
        'sma_10', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'ratio_sma10', 'ratio_sma20', 'ratio_sma50',
        'rsi_14', 'macd_line', 'macd_signal', 'macd_hist',
        'volatility_20d', 'bb_pct', 'bb_width',
        'vol_change_1d', 'vol_ratio'
    ]

    # The very last row has all features calculated up to the latest market close,
    # but its target_close is NaN. This is the vector to predict the next future day.
    latest_row = df.iloc[-1:][feature_cols].copy()

    # Dataset for training/testing (drop rows where features are NaN due to rolling windows,
    # and drop rows where target is NaN)
    clean_df = df.dropna(subset=feature_cols + ['target_close']).reset_index(drop=True)

    if len(clean_df) < 30:
        raise ValueError(f"Insufficient samples after feature engineering ({len(clean_df)} remaining). Need >= 30.")

    return clean_df, feature_cols, 'target_close', latest_row, df
