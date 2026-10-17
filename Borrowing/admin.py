from django.contrib import admin
from .models import Borrower, BorrowRecord
from datetime import date


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'student_id', 'phone', 'department')
    search_fields = ('full_name', 'student_id')
    list_filter = ('department',)


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ('item', 'borrower', 'date_borrowed', 'due_date', 'date_returned', 'state')
    list_filter = ('status', 'date_borrowed')
    search_fields = ('item__name', 'borrower__full_name')
    date_hierarchy = 'date_borrowed'
    actions = ['mark_returned']

    @admin.display(description='Status')
    def state(self, obj):
        return obj.display_status

    def get_readonly_fields(self, request, obj=None):
        # the item of an existing record should not be swapped
        return ('item',) if obj else ()

    @admin.action(description='Mark selected records as returned')
    def mark_returned(self, request, queryset):
        count = 0
        for record in queryset.active():
            record.date_returned = date.today()
            record.save()
            count += 1
        self.message_user(request, f"{count} record(s) marked as returned.")