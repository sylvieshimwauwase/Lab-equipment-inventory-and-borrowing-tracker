import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

from Analytics.features import FEATURES

MODEL_DIR = Path(__file__).resolve().parents[2] / 'ml_model'


def make_synthetic(rows, seed=42):
    """Fake loans with patterns we define: long loans, Fridays, fair items
    and borrowers with a late history are more likely to be returned late."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        'loan_days': rng.integers(3, 22, rows),
        'weekday': rng.integers(0, 7, rows),
        'prior_loans': rng.integers(0, 15, rows),
        'item_times_borrowed': rng.integers(0, 30, rows),
        'item_fair': rng.integers(0, 2, rows),
    })
    df['prior_late_rate'] = np.where(
        df['prior_loans'] == 0, 0.0, rng.beta(1.2, 4, rows)).round(3)

    logit = (-2.2
             + 0.15 * (df['loan_days'] - 10)
             + 3.0 * df['prior_late_rate']
             + 0.6 * (df['weekday'] == 4)
             + 0.5 * df['item_fair']
             - 0.05 * df['prior_loans'])
    probability = 1 / (1 + np.exp(-logit))
    df['returned_late'] = (rng.random(rows) < probability).astype(int)
    return df


def read_from_api(url, user, password):
    response = requests.get(url, auth=(user, password), timeout=60)
    response.raise_for_status()
    return pd.DataFrame(response.json())


class Command(BaseCommand):
    help = "Train the late-return risk model and save it to Analytics/ml_model/."

    def add_arguments(self, parser):
        parser.add_argument('--source', choices=['synthetic', 'api', 'both'],
                            default='synthetic')
        parser.add_argument('--rows', type=int, default=2000,
                            help='Number of synthetic rows.')
        parser.add_argument('--api-url',
                            default='http://127.0.0.1:8000/api/training-data/')
        parser.add_argument('--user')
        parser.add_argument('--password')

    def handle(self, *args, **options):
        frames = []
        if options['source'] in ('api', 'both'):
            if not options['user'] or not options['password']:
                raise CommandError('--user and --password are needed for --source api.')
            api_df = read_from_api(options['api_url'], options['user'], options['password'])
            self.stdout.write(f'Read {len(api_df)} rows from the API.')
            if len(api_df):
                frames.append(api_df[FEATURES + ['returned_late']])
        if options['source'] in ('synthetic', 'both'):
            frames.append(make_synthetic(options['rows']))
            self.stdout.write(f"Generated {options['rows']} synthetic rows.")

        if not frames:
            raise CommandError('No training data.')
        data = pd.concat(frames, ignore_index=True)
        X, y = data[FEATURES], data['returned_late']
        if y.nunique() < 2:
            raise CommandError('The data has only one outcome, so nothing can be learned.')

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y)

        model = RandomForestClassifier(
            n_estimators=200, max_depth=6, class_weight='balanced', random_state=42)
        model.fit(X_train, y_train)

        accuracy = accuracy_score(y_test, model.predict(X_test))
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])

        MODEL_DIR.mkdir(exist_ok=True)
        joblib.dump({'model': model, 'features': FEATURES}, MODEL_DIR / 'late_return_model.joblib')
        metrics = {
            'trained_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'source': options['source'],
            'rows': int(len(data)),
            'late_share': round(float(y.mean()), 3),
            'accuracy': round(float(accuracy), 3),
            'auc': round(float(auc), 3),
            'importances': {f: round(float(i), 3)
                            for f, i in zip(FEATURES, model.feature_importances_)},
        }
        (MODEL_DIR / 'metrics.json').write_text(json.dumps(metrics, indent=2))

        self.stdout.write(self.style.SUCCESS(
            f"Model saved. Accuracy {metrics['accuracy']}, AUC {metrics['auc']} "
            f"on {metrics['rows']} rows."))
        for name, value in sorted(metrics['importances'].items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {name}: {value}')