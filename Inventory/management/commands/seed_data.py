import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from Inventory.models import Category, Item
from Borrowing.models import Borrower, BorrowRecord

CATALOG = {
    'Computers': [('Dell Laptop', 'DL'), ('HP Desktop', 'HD'), ('Raspberry Pi Kit', 'RP')],
    'Projectors': [('Epson Projector', 'EP'), ('BenQ Projector', 'BQ')],
    'Cables': [('HDMI Cable', 'HC'), ('Ethernet Cable', 'EC'), ('Power Extension', 'PE')],
    'Lab Instruments': [('Digital Multimeter', 'DM'), ('Oscilloscope', 'OS'), ('Microscope', 'MS')],
}
UNITS_PER_ITEM = 3
DEPARTMENTS = ['Computer Science', 'Data Science', 'Information Systems',
               'Electronics', 'Software Engineering']


class Command(BaseCommand):
    help = "Fill the database with sample categories, items, borrowers and borrow records."

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Delete ALL existing data in these four tables first.')
        parser.add_argument('--borrowers', type=int, default=15)

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker()
        today = date.today()

        if options['clear']:
            BorrowRecord.objects.all().delete()
            Item.objects.all().delete()
            Category.objects.all().delete()
            Borrower.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing data cleared.'))

        # 1. Parents first: Category
        categories = {}
        for name in CATALOG:
            categories[name], _ = Category.objects.get_or_create(
                name=name, defaults={'description': f'{name} used in the labs.'})

        # 1. Parents first: Borrower
        for n in range(1, options['borrowers'] + 1):
            Borrower.objects.get_or_create(
                student_id=f'2024{n:03d}',
                defaults={
                    'full_name': fake.name(),
                    'phone': '+2507' + ''.join(random.choices('0123456789', k=8)),
                    'email': fake.unique.email(),
                    'department': random.choice(DEPARTMENTS),
                })

        # 2. Children: Item (needs Category)
        for cat_name, products in CATALOG.items():
            for product, prefix in products:
                for unit in range(1, UNITS_PER_ITEM + 1):
                    condition = random.choices(
                        ['good', 'fair', 'damaged'], weights=[70, 20, 10])[0]
                    Item.objects.get_or_create(
                        serial_number=f'{prefix}-{unit:03d}',
                        defaults={
                            'name': product,
                            'category': categories[cat_name],
                            'condition': condition,
                        })

        # 3. Last: BorrowRecord (needs Item and Borrower)
        borrowers = list(Borrower.objects.all())
        usable = list(Item.objects.filter(is_available=True))
        random.shuffle(usable)
        sample = usable[:min(14, len(usable))]

        created = 0
        for i, item in enumerate(sample):
            borrower = random.choice(borrowers)
            if i < 3:            # overdue: not returned, due date already passed
                borrowed = today - timedelta(days=random.randint(15, 25))
                due = today - timedelta(days=random.randint(2, 8))
                returned = None
            elif i < 7:          # on loan, still within the deadline
                borrowed = today - timedelta(days=random.randint(1, 5))
                due = today + timedelta(days=random.randint(3, 10))
                returned = None
            else:                # returned in the past
                borrowed = today - timedelta(days=random.randint(20, 40))
                due = borrowed + timedelta(days=10)
                returned = borrowed + timedelta(days=random.randint(2, 9))

            BorrowRecord.objects.create(
                item=item, borrower=borrower, date_borrowed=borrowed,
                due_date=due, date_returned=returned)
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {Category.objects.count()} categories, {Item.objects.count()} items, '
            f'{Borrower.objects.count()} borrowers, {BorrowRecord.objects.count()} records '
            f'({created} new).'))