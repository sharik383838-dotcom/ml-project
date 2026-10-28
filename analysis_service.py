"""
Technical Analysis Service for StockLens.
Calculates technical indicators from historical price data using pandas/numpy.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_sma(prices, window):
    """Calculate Simple Moving Average."""
    return prices.rolling(window=window).mean()


def calculate_ema(prices, span):
    """Calculate Exponential Moving Average."""
    return prices.ewm(span=span, adjust=False).mean()


def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices, window=20, num_std=2):
    """Calculate Bollinger Bands."""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


def run_full_analysis(history_data):
    """
    Run complete technical analysis on historical data.
    
    Args:
        history_data: List of dicts with date, open, high, low, close, volume
    
    Returns:
        Dict with all technical indicators and quantitative summary.
    """
    if not history_data or len(history_data) < 30:
        return {'error': 'Insufficient data for analysis. Need at least 30 data points.'}

    try:
        df = pd.DataFrame(history_data)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.sort_values('date').reset_index(drop=True)

        close = df['close'].astype(float)
        volume = df['volume'].astype(float)

        # Moving Averages
        sma_20 = calculate_sma(close, 20)
        sma_50 = calculate_sma(close, 50)
        sma_200 = calculate_sma(close, 200)
        ema_20 = calculate_ema(close, 20)

        # RSI
        rsi = calculate_rsi(close, 14)

        # MACD
        macd_line, signal_line, macd_hist = calculate_macd(close)

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)

        # Daily returns
        daily_returns = close.pct_change()

        # Volatility (annualized)
        volatility = daily_returns.std() * np.sqrt(252) * 100

        # Average volume
        avg_volume = volume.mean()

        # Build response data
        dates = [d.strftime('%Y-%m-%d') for d in df['date']]
        
        def safe_round_list(series):
            return [round(float(v), 2) if pd.notna(v) else None for v in series]

        result = {
            'dates': dates,
            'indicators': {
                'sma_20': safe_round_list(sma_20),
                'sma_50': safe_round_list(sma_50),
                'sma_200': safe_round_list(sma_200),
                'ema_20': safe_round_list(ema_20),
                'rsi': safe_round_list(rsi),
                'macd': safe_round_list(macd_line),
                'macd_signal': safe_round_list(signal_line),
                'macd_histogram': safe_round_list(macd_hist),
                'bb_upper': safe_round_list(bb_upper),
                'bb_middle': safe_round_list(bb_middle),
                'bb_lower': safe_round_list(bb_lower),
                'daily_returns': safe_round_list(daily_returns * 100),
            },
            'stats': {
                'volatility': round(float(volatility), 2) if pd.notna(volatility) else None,
                'avg_volume': round(float(avg_volume), 0) if pd.notna(avg_volume) else None,
                'current_rsi': round(float(rsi.iloc[-1]), 2) if pd.notna(rsi.iloc[-1]) else None,
                'current_macd': round(float(macd_line.iloc[-1]), 2) if pd.notna(macd_line.iloc[-1]) else None,
                'current_sma_20': round(float(sma_20.iloc[-1]), 2) if pd.notna(sma_20.iloc[-1]) else None,
                'current_sma_50': round(float(sma_50.iloc[-1]), 2) if pd.notna(sma_50.iloc[-1]) else None,
                'current_sma_200': round(float(sma_200.iloc[-1]), 2) if pd.notna(sma_200.iloc[-1]) else None,
                'current_ema_20': round(float(ema_20.iloc[-1]), 2) if pd.notna(ema_20.iloc[-1]) else None,
            },
            'summary': _build_quantitative_summary(close, sma_20, sma_50, sma_200, rsi, macd_line, 
                                                     signal_line, volatility, daily_returns, bb_upper, bb_lower),
        }

        # Performance metrics
        current_price = float(close.iloc[-1])
        if len(close) > 5:
            result['stats']['return_1w'] = round(((current_price / float(close.iloc[-5])) - 1) * 100, 2)
        if len(close) > 22:
            result['stats']['return_1m'] = round(((current_price / float(close.iloc[-22])) - 1) * 100, 2)
        if len(close) > 66:
            result['stats']['return_3m'] = round(((current_price / float(close.iloc[-66])) - 1) * 100, 2)
        if len(close) > 252:
            result['stats']['return_1y'] = round(((current_price / float(close.iloc[-252])) - 1) * 100, 2)

        return result

    except Exception as e:
        logger.error(f'Error running analysis: {e}')
        return {'error': f'Analysis calculation failed: {str(e)}'}


def _build_quantitative_summary(close, sma_20, sma_50, sma_200, rsi, macd, signal, volatility, daily_returns, bb_upper, bb_lower):
    """Build a neutral quantitative summary from technical indicators."""
    summary = []
    current_price = float(close.iloc[-1])

    # SMA Analysis
    if pd.notna(sma_20.iloc[-1]):
        sma20_val = float(sma_20.iloc[-1])
        status = 'Above' if current_price > sma20_val else 'Below'
        summary.append({
            'label': f'{status} SMA 20',
            'value': f'{sma20_val:.2f}',
            'description': 'Short-term trend based on 20-day simple moving average.',
            'signal': 'bullish' if current_price > sma20_val else 'bearish'
        })

    if pd.notna(sma_50.iloc[-1]):
        sma50_val = float(sma_50.iloc[-1])
        status = 'Above' if current_price > sma50_val else 'Below'
        summary.append({
            'label': f'{status} SMA 50',
            'value': f'{sma50_val:.2f}',
            'description': 'Medium-term trend based on 50-day simple moving average.',
            'signal': 'bullish' if current_price > sma50_val else 'bearish'
        })

    if pd.notna(sma_200.iloc[-1]):
        sma200_val = float(sma_200.iloc[-1])
        status = 'Above' if current_price > sma200_val else 'Below'
        summary.append({
            'label': f'{status} SMA 200',
            'value': f'{sma200_val:.2f}',
            'description': 'Long-term trend based on 200-day simple moving average.',
            'signal': 'bullish' if current_price > sma200_val else 'bearish'
        })

    # RSI
    if pd.notna(rsi.iloc[-1]):
        rsi_val = float(rsi.iloc[-1])
        if rsi_val > 70:
            rsi_status = 'Overbought'
            rsi_signal = 'bearish'
        elif rsi_val < 30:
            rsi_status = 'Oversold'
            rsi_signal = 'bullish'
        else:
            rsi_status = 'Neutral'
            rsi_signal = 'neutral'
        summary.append({
            'label': f'RSI: {rsi_val:.1f} ({rsi_status})',
            'value': f'{rsi_val:.1f}',
            'description': f'14-day RSI indicates {"potential overbought conditions" if rsi_val > 70 else "potential oversold conditions" if rsi_val < 30 else "neutral momentum"}.',
            'signal': rsi_signal
        })

    # MACD
    if pd.notna(macd.iloc[-1]) and pd.notna(signal.iloc[-1]):
        macd_val = float(macd.iloc[-1])
        signal_val = float(signal.iloc[-1])
        cross = 'Above' if macd_val > signal_val else 'Below'
        summary.append({
            'label': f'MACD {cross} Signal',
            'value': f'{macd_val:.2f}',
            'description': f'MACD line is {"above" if macd_val > signal_val else "below"} the signal line.',
            'signal': 'bullish' if macd_val > signal_val else 'bearish'
        })

    # Volatility
    if pd.notna(volatility):
        vol_val = float(volatility)
        if vol_val > 40:
            vol_status = 'High'
        elif vol_val > 20:
            vol_status = 'Moderate'
        else:
            vol_status = 'Low'
        summary.append({
            'label': f'Volatility: {vol_val:.1f}% ({vol_status})',
            'value': f'{vol_val:.1f}%',
            'description': f'Annualized historical volatility is {vol_status.lower()}.',
            'signal': 'neutral'
        })

    # Bollinger Band position
    if pd.notna(bb_upper.iloc[-1]) and pd.notna(bb_lower.iloc[-1]):
        bb_up = float(bb_upper.iloc[-1])
        bb_lo = float(bb_lower.iloc[-1])
        if current_price > bb_up:
            bb_status = 'Above Upper Band'
            bb_signal = 'bearish'
        elif current_price < bb_lo:
            bb_status = 'Below Lower Band'
            bb_signal = 'bullish'
        else:
            bb_status = 'Within Bands'
            bb_signal = 'neutral'
        summary.append({
            'label': f'Bollinger: {bb_status}',
            'value': f'Upper: {bb_up:.2f} / Lower: {bb_lo:.2f}',
            'description': f'Price is {bb_status.lower()} relative to 20-day Bollinger Bands.',
            'signal': bb_signal
        })

    # Recent performance
    if len(close) > 22:
        month_return = ((current_price / float(close.iloc[-22])) - 1) * 100
        summary.append({
            'label': f'1M Return: {month_return:.1f}%',
            'value': f'{month_return:.1f}%',
            'description': 'Price return over the last ~22 trading days.',
            'signal': 'bullish' if month_return > 0 else 'bearish'
        })

    return summary
