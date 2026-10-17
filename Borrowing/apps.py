from django.apps import AppConfig


class BorrowingConfig(AppConfig):
    name = "Borrowing"

    def ready(self):
        from . import signals
