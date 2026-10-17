from datetime import date

from django.db.models import Count, Q
from django.urls import include, path
from rest_framework import routers, serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Borrowing.models import Borrower, BorrowRecord
from Inventory.models import Category, Item


# ---------- Serializers: turn model objects into JSON ----------
class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'item_count']


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Item
        fields = ['id', 'name', 'serial_number', 'category', 'category_name',
                  'condition', 'is_available', 'date_added']


class BorrowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrower
        fields = ['id', 'full_name', 'student_id', 'phone', 'email', 'department']


class BorrowRecordSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    borrower_name = serializers.CharField(source='borrower.full_name', read_only=True)
    state = serializers.CharField(source='display_status', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = BorrowRecord
        fields = ['id', 'item', 'item_name', 'borrower', 'borrower_name',
                  'date_borrowed', 'due_date', 'date_returned',
                  'status', 'state', 'is_overdue']


# ---------- Viewsets: read-only endpoints ----------
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.annotate(item_count=Count('items')).order_by('name')


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ItemSerializer

    def get_queryset(self):
        qs = Item.objects.select_related('category')
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(serial_number__icontains=q))
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])
        if params.get('available') in ('true', 'false'):
            qs = qs.filter(is_available=(params['available'] == 'true'))
        return qs


class BorrowerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Borrower.objects.all()
    serializer_class = BorrowerSerializer


class BorrowRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BorrowRecordSerializer

    def get_queryset(self):
        qs = BorrowRecord.objects.select_related('item', 'borrower')
        status = self.request.query_params.get('status')
        if status == 'overdue':
            qs = qs.overdue()
        elif status == 'borrowed':
            qs = qs.active().filter(due_date__gte=date.today())
        elif status == 'returned':
            qs = qs.filter(status='returned')
        return qs


@api_view(['GET'])
def stats(request):
    """Summary numbers, the same ones as the dashboard cards."""
    return Response({
        'total_items': Item.objects.count(),
        'available_items': Item.objects.filter(is_available=True).count(),
        'borrowed': BorrowRecord.objects.active().count(),
        'overdue': BorrowRecord.objects.overdue().count(),
    })


# ---------- URLs ----------
router = routers.DefaultRouter()
router.register('categories', CategoryViewSet, basename='api-category')
router.register('items', ItemViewSet, basename='api-item')
router.register('borrowers', BorrowerViewSet, basename='api-borrower')
router.register('borrow-records', BorrowRecordViewSet, basename='api-borrowrecord')

urlpatterns = [
    path('stats/', stats, name='api-stats'),
    path('', include(router.urls)),
]