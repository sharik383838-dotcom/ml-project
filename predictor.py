"""
Stock Price Prediction Model Module.
Provides modular machine learning predictors (Random Forest, Gradient Boosting)
with chronological train/test splitting, performance metric calculation,
and out-of-sample forward estimates.
"""

import abc
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


class BaseStockPredictor(abc.ABC):
    """Abstract base class for modular stock price prediction models."""

    @abc.abstractmethod
    def fit(self, X_train, y_train):
        """Fit the model on training data."""
        pass

    @abc.abstractmethod
    def predict(self, X):
        """Generate predictions for feature matrix X."""
        pass

    @abc.abstractmethod
    def get_feature_importances(self, feature_names):
        """Return dict of feature names and their relative importance scores."""
        pass


class RandomForestStockPredictor(BaseStockPredictor):
    """
    Random Forest ensemble model for stock price estimation.
    Uses bagging of decision trees on financial technical features.
    """

    def __init__(self, n_estimators=100, max_depth=10, min_samples_split=4, random_state=42):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=random_state,
            n_jobs=-1
        )
        self.model_name = "Random Forest Regressor"

    def fit(self, X_train, y_train):
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        return self.model.predict(X)

    def get_feature_importances(self, feature_names):
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
            return {k: round(float(v), 4) for k, v in pairs[:8]}
        return {}


def train_and_evaluate_model(clean_df, feature_cols, target_col, latest_row, test_size=0.2, model_type='rf'):
    """
    Perform chronological train/test split (no data leakage), train the ML model,
    evaluate on unseen test data, and predict the next period price.

    Args:
        clean_df: DataFrame containing features and target_col
        feature_cols: List of feature column names
        target_col: Column name of target ('target_close')
        latest_row: Single row DataFrame containing the latest features (target is NaN)
        test_size: Fraction of historical data used for testing (default 0.2)
        model_type: 'rf' for RandomForest

    Returns:
        dict: Performance metrics, test comparison series, next price prediction, feature importances.
    """
    n_samples = len(clean_df)
    split_idx = int(n_samples * (1 - test_size))

    # Strict chronological split - NO shuffling to prevent lookahead bias / data leakage
    train_df = clean_df.iloc[:split_idx]
    test_df = clean_df.iloc[split_idx:]

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    # Instantiate model
    if model_type == 'gb':
        model = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)
        model_name = "Gradient Boosting Regressor"
    else:
        model = RandomForestStockPredictor(n_estimators=100, max_depth=10, min_samples_split=4, random_state=42)
        model_name = model.model_name

    # Train model
    model.fit(X_train, y_train)

    # Predict on test set
    y_pred_test = model.predict(X_test)

    # 1. Performance Metrics
    mae = float(mean_absolute_error(y_test, y_pred_test))
    mse = float(mean_squared_error(y_test, y_pred_test))
    rmse = float(np.sqrt(mse))
    
    # Mean Absolute Percentage Error (MAPE)
    mape = float(np.mean(np.abs((y_test.values - y_pred_test) / (y_test.values + 1e-8))) * 100.0)
    
    # R² score
    r2 = float(r2_score(y_test, y_pred_test))

    # Directional Accuracy: did the model predict the correct direction vs today's close?
    # Actual direction: target_close (tomorrow) - close (today)
    actual_diff = y_test.values - X_test['close'].values
    pred_diff = y_pred_test - X_test['close'].values
    correct_dir = np.sign(actual_diff) == np.sign(pred_diff)
    directional_acc = float(np.mean(correct_dir) * 100.0) if len(correct_dir) > 0 else 50.0

    # 2. Out-of-sample forward prediction (Next trading period)
    next_price_pred = float(model.predict(latest_row[feature_cols])[0])
    current_close = float(latest_row['close'].iloc[0])

    predicted_change = round(next_price_pred - current_close, 2)
    predicted_change_pct = round((predicted_change / current_close) * 100.0, 2)
    direction = "bullish" if predicted_change >= 0 else "bearish"

    # Estimated uncertainty interval (+/- 1.96 * RMSE)
    lower_bound = max(0.01, round(next_price_pred - 1.96 * rmse, 2))
    upper_bound = round(next_price_pred + 1.96 * rmse, 2)

    # 3. Test vs Actual chart data for comparison chart
    # Use dates from test_df if present
    test_dates = test_df['date'].astype(str).tolist() if 'date' in test_df.columns else [f"T-{len(test_df)-i}" for i in range(len(test_df))]
    
    # Feature importances
    feat_imp = model.get_feature_importances(feature_cols) if hasattr(model, 'get_feature_importances') else {}

    return {
        'modelName': model_name,
        'currentPrice': round(current_close, 2),
        'predictedPrice': round(next_price_pred, 2),
        'predictedChange': predicted_change,
        'predictedChangePercent': predicted_change_pct,
        'direction': direction,
        'uncertaintyInterval': {
            'lower': lower_bound,
            'upper': upper_bound
        },
        'metrics': {
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'mape': round(mape, 2),
            'directionalAccuracy': round(directional_acc, 2),
            'r2': round(r2, 4)
        },
        'chartComparison': {
            'dates': test_dates,
            'actualPrices': [round(float(v), 2) for v in y_test.values],
            'predictedPrices': [round(float(v), 2) for v in y_pred_test]
        },
        'featureImportances': feat_imp,
        'trainSamples': len(train_df),
        'testSamples': len(test_df)
    }
