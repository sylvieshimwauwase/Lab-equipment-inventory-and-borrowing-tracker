from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

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

    # Chart 1: items per category
    categories = Category.objects.annotate(item_count=Count('items')).order_by('name')
    category_chart = {
        'labels': [c.name for c in categories],
        'values': [c.item_count for c in categories],
    }

    # Chart 2: borrowings per month (last 6 months)
    months = last_months(6)
    monthly_chart = {
        'labels': [date(y, m, 1).strftime('%b %Y') for y, m in months],
        'values': [
            BorrowRecord.objects.filter(date_borrowed__year=y, date_borrowed__month=m).count()
            for y, m in months
        ],
    }

    related = BorrowRecord.objects.select_related('item', 'borrower')
    context = {
        'total_items': Item.objects.count(),
        'available_items': Item.objects.filter(is_available=True).count(),
        'borrowed_count': BorrowRecord.objects.active().count(),
        'overdue_count': BorrowRecord.objects.overdue().count(),
        'category_chart': category_chart,
        'monthly_chart': monthly_chart,
        'overdue_records': related.overdue().order_by('due_date')[:5],
        'due_soon_records': related.active().filter(
            due_date__gte=today, due_date__lte=today + timedelta(days=7)
        ).order_by('due_date')[:5],
        'recent_records': related.order_by('-date_borrowed', '-pk')[:5],
    }
    return render(request, 'dashboard.html', context)