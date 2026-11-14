from django.contrib import admin

from .models import RiskPrediction


@admin.register(RiskPrediction)
class RiskPredictionAdmin(admin.ModelAdmin):
    list_display = ('record', 'level', 'percent', 'model_trained_at', 'created_at')
    list_filter = ('level',)
    search_fields = ('record__item__name', 'record__borrower__full_name')
    readonly_fields = ('record', 'probability', 'level', 'model_trained_at', 'created_at')

    @admin.display(description='Risk %')
    def percent(self, obj):
        return f"{obj.percent}%"