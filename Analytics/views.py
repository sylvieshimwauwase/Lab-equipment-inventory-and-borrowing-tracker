import calendar

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .forms import RiskCheckForm
from .predictor import model_info, predict_borrowing

FEATURE_LABELS = {
    'borrow_days': 'Borrowing period (days)',
    'weekday': 'Day of the week',
    'prior_borrowings': "Borrower's returned borrowings",
    'prior_late_rate': "Borrower's past late-return rate",
    'item_times_borrowed': 'Times this item was borrowed',
    'item_fair': 'Item in fair condition',
}

ADVICE = {
    'low': 'No action needed. This borrowing is likely to come back on time.',
    'medium': 'Send the borrower a reminder a day before the due date.',
    'high': 'Consider a shorter borrowing period, and follow up with the borrower before the due date.',
}


def describe_features(features):
    """Turn raw model inputs into readable label and value pairs."""
    rows = []
    for key, label in FEATURE_LABELS.items():
        value = features[key]
        if key == 'weekday':
            value = calendar.day_name[value]
        elif key == 'prior_late_rate':
            value = f"{round(value * 100)}%"
        elif key == 'item_fair':
            value = 'Yes' if value else 'No'
        rows.append({'label': label, 'value': value})
    return rows


@login_required
def risk_check(request):
    form = RiskCheckForm(request.POST or None)
    result = None

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        result = predict_borrowing(
            data['item'], data['borrower'], data['date_borrowed'], data['due_date'])
        if result is None:
            messages.warning(
                request, 'The prediction model is not available. '
                         'Run: python manage.py train_model')
        else:
            result['percent'] = round(result['probability'] * 100)
            result['factors'] = describe_features(result['features'])
            result['advice'] = ADVICE[result['level']]
            result['item'] = data['item']
            result['borrower'] = data['borrower']

    info = model_info()
    importances = []
    if info:
        importances = sorted(
            ((FEATURE_LABELS.get(k, k), round(v * 100))
             for k, v in info['importances'].items()),
            key=lambda pair: -pair[1])

    return render(request, 'analytics/risk_check.html', {
        'form': form,
        'result': result,
        'info': info,
        'importances': importances,
    })