from datetime import date

from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Borrowing.models import Borrower
from Inventory.models import Item
from .predictor import model_info, predict_borrowing


class PredictionRequestSerializer(serializers.Serializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    borrower = serializers.PrimaryKeyRelatedField(queryset=Borrower.objects.all())
    date_borrowed = serializers.DateField(default=date.today)
    due_date = serializers.DateField()

    def validate(self, data):
        if data['due_date'] < data['date_borrowed']:
            raise serializers.ValidationError(
                {'due_date': 'Due date cannot be earlier than the borrow date.'})
        return data


@api_view(['POST'])
def predict(request):
    """Receive new borrowing data and return the late-return risk. Nothing is saved."""
    serializer = PredictionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    result = predict_borrowing(
        data['item'], data['borrower'], data['date_borrowed'], data['due_date'])
    if result is None:
        return Response({'detail': 'The prediction model is not available.'}, status=503)

    info = model_info() or {}
    return Response({
        'probability': result['probability'],
        'percent': round(result['probability'] * 100),
        'level': result['level'],
        'features': result['features'],
        'model': {
            'trained_at': info.get('trained_at'),
            'source': info.get('source'),
            'accuracy': info.get('accuracy'),
            'auc': info.get('auc'),
        },
    })