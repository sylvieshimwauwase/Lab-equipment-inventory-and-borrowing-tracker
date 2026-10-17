# Lab Equipment Inventory and Borrowing Tracker: Project Report

Course: Web Technologies and API Services
Group: 5

| Member | Student ID |
|---|---|
| SHIMWA UWASE Sylvie | 20251MBI007 |
| ISENGWE Olga | 20251MBI013 |
| RUKUNDO Patrick | 20251MBI057 |

Date: [17/10/2026]

## 1. Introduction

In school laboratories, equipment such as laptops, projectors and cables is often
lent from memory or on paper. Items get lost, nobody knows what is available, and
late returns go unnoticed. Our system records equipment, tracks every loan, and
shows availability and overdue items on a dashboard.

## 2. System description

- Manage categories, equipment items and borrowers
- Lend an item and record its return
- Detect overdue items automatically
- Dashboard with statistics, charts and warning tables
- Two roles (Staff and Manager) and a read-only JSON API

## 3. Design

### 3.1 Applications
| App | Responsibility |
|---|---|
| Inventory | Categories and items |
| Borrowing | Borrowers and borrow records |

### 3.2 Database and relationships
[Insert the ER diagram: docs/er_diagram.png]

| Relationship | Cardinality | Explanation |
|---|---|---|
| Category to Item | 1:N | A category holds many items; an item has one category |
| Item to BorrowRecord | 1:N | An item can be lent many times over time |
| Borrower to BorrowRecord | 1:N | A borrower can have many loans |
| Item and Borrower | M:N | Resolved through BorrowRecord, the junction table |

### 3.3 URL structure
The project `urls.py` includes each app's `urls.py` with `include()`. Dynamic
URLs such as `/inventory/items/<int:pk>/` pass the record id to the view.
Example flow: browser requests `/inventory/items/5/`, Django matches the pattern,
calls `ItemDetailView`, which loads the item and renders `item_detail.html`
as the response.

## 4. Implementation

- **Models and migrations:** four models with `PROTECT` foreign keys and two
  database `CheckConstraint`s on dates.
- **Business rules in the model:** `clean()` rejects a due date before the borrow
  date, a damaged item, and an item that is already borrowed. Because the rules
  live in the model, the Django admin follows them too.
- **Computed fields:** `is_available` and the overdue status are calculated, not
  typed, so they cannot contradict the data. Signals update an item whenever a
  borrow record is created, changed or deleted.
- **Forms:** ModelForms with validation (unique serial number, phone format).
- **Views:** class-based views for CRUD, function views for the list pages and
  the return action (POST only, wrapped in a transaction).
- **Templates:** `base.html` holds the AdminLTE navbar and sidebar; every page
  extends it. Shared `form.html`, `confirm_delete.html` and `pagination.html`.
- **Security:** login required everywhere; Staff and Manager groups with
  `PermissionRequiredMixin`; credentials in `.env`.
- **API:** Django REST Framework serializers and read-only viewsets.
- **Tests:** 17 tests covering borrowing, returning, validation, overdue logic,
  permissions and the API.
- **Deployment:** MySQL on Aiven (SSL), app hosted on Render with WhiteNoise.

## 5. Screenshots
[Insert each screenshot with a one-line caption: login, dashboard, items with
filter, item detail, validation error, delete confirmation, borrow form,
overdue row, Staff user without delete buttons, Django admin, Aiven tables,
API response, test run.]

## 6. Challenges and solutions

| Challenge | Solution |
|---|---|
| `ModuleNotFoundError: dotenv` | Anaconda and the venv were mixed; we used `python -m pip` inside the venv |
| Connecting to MySQL on Aiven over SSL | Downloaded the CA certificate and passed it in the database `OPTIONS` |
| Item availability going out of sync | Moved the logic from views into the model and signals |
| Quantity conflicted with availability | Each item row became one physical unit |
| Deleting a borrower erased history | Switched from `CASCADE` to `PROTECT` with a friendly message |
| Bootstrap did not colour Django error messages | Mapped the `error` tag to `danger` in `MESSAGE_TAGS` |

## 7. Conclusion and future work

The system meets its goal of tracking equipment and loans reliably. Possible
improvements: email reminders for overdue items, CSV export, a barcode scanner
for serial numbers, and write access in the API with token authentication.

## 8. Group contributions

| Member | Role | Contribution |
|---|---|---|
| SHIMWA UWASE Sylvie (20251MBI007) | Project lead and main developer | Project setup and the two apps; MySQL on Aiven with `.env`; models, migrations and database constraints; business rules, signals and availability logic; forms and validation; views and URL routing; borrow and return workflow; Staff and Manager roles; REST API; deployment on Render; integration of all members' work |
| ISENGWE Olga (20251MBI013) | Interface developer | AdminLTE integration and `base.html`; dashboard cards, charts and the overdue and due-soon tables; list, detail and form templates; search, filters and pagination in the templates; colour theme (`custom.css`); 404 and 500 pages; screenshots |
| RUKUNDO Patrick (20251MBI057) | Data, testing and documentation | Django admin configuration; sample data command (`seed_data`); automated tests; ER diagram and cardinality explanation; README and project report; demo preparation and final submission checklist |

All members tested the application together, reviewed each other's work, and prepared to explain
the whole system during the demonstration.