# Lab Equipment Inventory and Borrowing Tracker: Project Report

Course: Web Technologies and API Services
Group: 5

| Member | Student ID |
|---|---|
| SHIMWA UWASE Sylvie | 20251MBI007 |
| ISENGWE Olga | 20251MBI013 |
| RUKUNDO Patrick | 20251MBI057 |

Date: [14/11/2026]

## 1. Introduction

In school laboratories, equipment such as laptops, projectors and cables is often
lent from memory or on paper. Items get lost, nobody knows what is available, and
late returns go unnoticed. Our system records equipment, tracks every borrowing,
and predicts which borrowings are likely to be returned late, so staff can act
before an item becomes overdue.

## 2. System description

- Manage categories, equipment items and borrowers
- Lend an item and record its return
- Detect overdue items automatically
- Dashboard with statistics, charts and warning tables
- Machine learning prediction of late returns, shown on the dashboard
- Two roles (Staff and Manager) and a JSON API

## 3. Design

### 3.1 Applications
| App | Responsibility |
|---|---|
| Inventory | Categories and items |
| Borrowing | Borrowers and borrow records |
| Analytics | Feature building, model training, prediction and the Risk Check page |

### 3.2 Database and relationships
[Insert the ER diagram: docs/er_diagram.png]

| Relationship | Cardinality | Explanation |
|---|---|---|
| Category to Item | 1:N | A category holds many items; an item has one category |
| Item to BorrowRecord | 1:N | An item can be borrowed many times over time |
| Borrower to BorrowRecord | 1:N | A borrower can have many borrowings |
| Item and Borrower | M:N | Resolved through BorrowRecord, the junction table |
| BorrowRecord to RiskPrediction | 1:1 | Each active borrowing has one current prediction |

### 3.3 URL structure
The project `urls.py` includes each app's `urls.py` with `include()`. Dynamic
URLs such as `/inventory/items/<int:pk>/` pass the record id to the view.
Example flow: the browser requests `/inventory/items/5/`, Django matches the
pattern, calls `ItemDetailView`, which loads the item and renders `item_detail.html`.

## 4. Implementation

- **Models and migrations:** five models with `PROTECT` foreign keys and two
  database `CheckConstraint`s on dates.
- **Business rules in the model:** `clean()` rejects a due date before the borrow
  date, a damaged item, and an item that is already borrowed, so the Django
  admin follows the same rules as the forms.
- **Computed fields:** availability and overdue status are calculated, not typed.
  Signals update an item whenever a borrow record is created, changed or deleted.
- **Forms, views and templates:** ModelForms with validation, class-based views
  for CRUD, and one `base.html` with the AdminLTE navbar and sidebar.
- **Security:** login required everywhere; Staff and Manager groups with
  `PermissionRequiredMixin`; credentials in `.env`.
- **API:** Django REST Framework serializers and read-only viewsets, plus a
  prediction endpoint.
- **Deployment:** PostgreSQL on Neon, app hosted on Render with WhiteNoise.

## 5. Machine learning component

### 5.1 Goal
Predict whether a borrowing will be returned after its due date.

### 5.2 Data
- **From an API:** the training command reads our own `/api/training-data/` endpoint,
  which returns one row per returned borrowing.
- **Synthetic data:** real history is small, so synthetic rows are generated with
  assumed patterns (longer borrowing periods, borrowers with a late history and
  items in fair condition are riskier). The model card on the dashboard says so.

### 5.3 Features
borrowing period, weekday, the borrower's returned borrowings, the borrower's
past late rate, how often the item was borrowed, and whether it is in fair condition.
One function (`record_features`) builds them for both training and prediction,
which prevents mismatches. Only history before the borrow date is used.

### 5.4 Model and evaluation
Random forest classifier (scikit-learn), 75% training and 25% testing.

| Metric | Value |
|---|---|
| Accuracy | [e.g. 0.68] |
| AUC | [e.g. 0.72] |
| Training rows | [e.g. 2007] |

The strongest factors were the borrowing period and the borrower's late-return
rate. Accuracy is modest because the synthetic data contains random noise.

### 5.5 Deployment in Django
- `predictor.py` loads the saved model and reloads it when the file changes.
- If the model file is missing, the application keeps working without scores.
- A signal scores every new borrowing and stores a `RiskPrediction`. Errors are
  logged and never block a borrowing.
- The Risk Check page and `POST /api/predict/` score new data without saving it.

### 5.6 Dashboard
At-risk borrowings table, risk-level chart, KPI boxes, feature importance chart
and a model card (training date, source, rows, accuracy, AUC).

### 5.7 Retraining workflow
Collect data through the API, train, evaluate, rescore, and commit the new model
file. Training is done locally, because the hosting disk is temporary.

### 5.8 Limitations
Part of the training data is synthetic; the model predicts risk and does not
guarantee behaviour; accuracy should improve as real borrowings accumulate.

## 6. Testing
38 automated tests cover borrowing and returning, validation, overdue logic,
permissions, the REST API, feature building, prediction, the fallback when the
model is missing, the scoring signal, the Risk Check page and the dashboard.

## 7. Screenshots
[Insert each screenshot with a one-line caption: login, dashboard (top and
prediction section), items with filter, item detail, validation error, delete
confirmation, borrow form, record list with risk column, Risk Check result,
Staff user without delete buttons, Django admin, database tables, API
response, test run.]

## 8. Challenges and solutions

| Challenge | Solution |
|---|---|
| `ModuleNotFoundError: dotenv` | Anaconda and the venv were mixed; we used `python -m pip` inside the venv |
| Item availability going out of sync | Moved the logic from views into the model and signals |
| Deleting a borrower erased history | Switched from `CASCADE` to `PROTECT` with a friendly message |
| Aiven's free MySQL plan was retired | Migrated to PostgreSQL on Neon; only the driver and settings changed, because Django's ORM hides the database |
| Real data had only on-time returns, so no model could be trained | Added synthetic data and the `--source both` option |
| A prediction error could block borrowing | Wrapped the signal in error handling and made the model optional |

## 9. Conclusion and future work

The system tracks equipment and borrowings reliably, and now helps staff act
before items become overdue. Possible improvements: email reminders for high-risk
borrowings, CSV export, scheduled retraining, and token authentication for API writes.

## 10. Group contributions

| Member | Role | Contribution |
|---|---|---|
| SHIMWA UWASE Sylvie (20251MBI007) | Project lead and main developer | Project setup, apps, database, models, business rules, signals, views, roles, REST API, machine learning pipeline, deployment |
| ISENGWE Olga (20251MBI013) | Interface developer | AdminLTE integration, dashboard and prediction widgets, templates, theme, error pages, screenshots |
| RUKUNDO Patrick (20251MBI057) | Data, testing and documentation | Admin configuration, seed data, automated tests, ER diagram, README and report, demo preparation |

All members tested the application together and prepared to explain the whole system.