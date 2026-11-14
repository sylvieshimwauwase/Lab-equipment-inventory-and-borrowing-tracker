from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F
from django.shortcuts import render

from Analytics.models import RiskPrediction
from Analytics.predictor import model_info
from Analytics.views import FEATURE_LABELS
from Borrowing.models import BorrowRecord
from .models import Category, Item


def last_months(n=6):
    """Return the last n months as (year, month) pairs, oldest first."""
    today = date.today()
    year, month = today.year, today.month
    months = []
    for _ in range(n):
        months.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(months))


@login_required
def dashboard(request):
    today = date.today()

    # ---------- Chart: items per category ----------
    categories = Category.objects.annotate(item_count=Count('items')).order_by('name')
    category_chart = {
        'labels': [c.name for c in categories],
        'values': [c.item_count for c in categories],
    }

    # ---------- Chart: borrowings per month ----------
    months = last_months(6)
    monthly_chart = {
        'labels': [date(y, m, 1).strftime('%b %Y') for y, m in months],
        'values': [
            BorrowRecord.objects.filter(date_borrowed__year=y, date_borrowed__month=m).count()
            for y, m in months
        ],
    }

    # ---------- Machine learning: risk of active borrowings ----------
    active_risks = RiskPrediction.objects.filter(record__status='borrowed')
    level_counts = {row['level']: row['n']
                    for row in active_risks.values('level').annotate(n=Count('id'))}
    risk_chart = {
        'labels': ['Low', 'Medium', 'High'],
        'values': [level_counts.get('low', 0),
                   level_counts.get('medium', 0),
                   level_counts.get('high', 0)],
    }
    average = active_risks.aggregate(avg=Avg('probability'))['avg']
    at_risk = (active_risks.select_related('record__item', 'record__borrower')
               .order_by('-probability')[:6])
    unscored = BorrowRecord.objects.active().filter(risk__isnull=True).count()

    # Historical late-return rate, from real returned borrowings
    returned = BorrowRecord.objects.filter(date_returned__isnull=False)
    returned_total = returned.count()
    returned_late = returned.filter(date_returned__gt=F('due_date')).count()
    late_rate = round(returned_late / returned_total * 100) if returned_total else None

    info = model_info()
    importance_chart = None
    if info:
        pairs = sorted(info['importances'].items(), key=lambda p: -p[1])
        importance_chart = {
            'labels': [FEATURE_LABELS.get(k, k) for k, _ in pairs],
            'values': [round(v * 100) for _, v in pairs],
        }

    related = BorrowRecord.objects.select_related('item', 'borrower')
    context = {
        'total_items': Item.objects.count(),
        'available_items': Item.objects.filter(is_available=True).count(),
        'borrowed_count': BorrowRecord.objects.active().count(),
        'overdue_count': BorrowRecord.objects.overdue().count(),

        'category_chart': category_chart,
        'monthly_chart': monthly_chart,
        'risk_chart': risk_chart,
        'importance_chart': importance_chart,

        'high_risk_count': level_counts.get('high', 0),
        'average_risk': round(average * 100) if average is not None else None,
        'late_rate': late_rate,
        'at_risk': at_risk,
        'unscored': unscored,
        'info': info,

        'overdue_records': related.overdue().order_by('due_date')[:5],
        'due_soon_records': related.active().filter(
            due_date__gte=today, due_date__lte=today + timedelta(days=7)
        ).order_by('due_date')[:5],
        'recent_records': related.order_by('-date_borrowed', '-pk')[:5],
    }
    return render(request, 'dashboard.html', context)