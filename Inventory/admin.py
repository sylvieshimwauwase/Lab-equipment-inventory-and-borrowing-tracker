from django.contrib import admin
from .models import Category, Item


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'category', 'condition', 'is_available')
    list_filter = ('category', 'condition', 'is_available')
    search_fields = ('name', 'serial_number')