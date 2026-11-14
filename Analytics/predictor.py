import json
import logging
from pathlib import Path

import joblib
import pandas as pd

from .features import FEATURES, record_features

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / 'ml_model'
MODEL_FILE = MODEL_DIR / 'late_return_model.joblib'
METRICS_FILE = MODEL_DIR / 'metrics.json'

LOW_BELOW = 0.35
HIGH_FROM = 0.60

_cache = {'mtime': None, 'bundle': None}


def _load():
    """Load the saved model. It is reloaded automatically if the file changes.
    Returns None when the file is missing or unreadable."""
    if not MODEL_FILE.exists():
        return None
    mtime = MODEL_FILE.stat().st_mtime
    if _cache['mtime'] != mtime:
        try:
            _cache['bundle'] = joblib.load(MODEL_FILE)
        except Exception:
            logger.exception('Could not load the risk model.')
            _cache['bundle'] = None
        _cache['mtime'] = mtime
    return _cache['bundle']


def model_info():
    """Metrics saved at training time (accuracy, AUC, importances), or None."""
    if not METRICS_FILE.exists():
        return None
    try:
        return json.loads(METRICS_FILE.read_text())
    except (OSError, ValueError):
        return None


def risk_level(probability):
    if probability < LOW_BELOW:
        return 'low'
    if probability < HIGH_FROM:
        return 'medium'
    return 'high'


def predict_features(features):
    """Probability (0 to 1) that a borrowing is returned late, or None."""
    bundle = _load()
    if bundle is None:
        return None
    row = pd.DataFrame([features])[FEATURES]
    return float(bundle['model'].predict_proba(row)[0][1])


def predict_borrowing(item, borrower, date_borrowed, due_date):
    """Score one borrowing. Returns {'probability', 'level', 'features'} or None."""
    features = record_features(item, borrower, date_borrowed, due_date)
    probability = predict_features(features)
    if probability is None:
        return None
    return {
        'probability': round(probability, 4),
        'level': risk_level(probability),
        'features': features,
    }