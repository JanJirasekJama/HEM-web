# HEM subagent plans

Shared rules for every implementation agent:

- Do not edit `backend/tests/**` unless the orchestrator explicitly grants permission.
- Keep module boundaries: a business module may depend on `app.core` and `app.shared`; do not import another business module's private service/model from inside business logic.
- Use public contracts for cross-module reads where practical: HTTP contract shape, read-only query helpers, DTO-like schemas, or reporting views.
- Preserve TDD: make the assigned failing tests pass, then run at least the assigned test file and report commands/results.
- Keep writes inside the owned module paths listed below. If a shared file must change, explain why before doing it.
- Use Redis via `app.shared.notifications.NotificationQueue` for notification/event fan-out; never hand-roll a second queue.

## Area 3: Catalogs

Owner paths: `backend/app/modules/catalog/**`

Plan:
- Implement catalog tables and REST endpoints for service categories, services, due terms, inventory items, hotel rooms, housekeeping minibar items, photo task types and email recipients.
- Support active/inactive filtering while preserving direct reads of inactive historic items.
- Keep catalog entities generic, without importing business module models.

Tests: `backend/tests/test_catalogs.py`

## Area 4: Inventory

Owner paths: `backend/app/modules/inventory/**`

Plan:
- Implement daily entries for `wellness`, `minibar` and `lobby` with item rows and custom lobby rows.
- Support by-date loading, updates, archive filtering/deletion and monthly totals.
- Snapshot names/prices from request/catalog-facing payloads so historical reports remain readable.

Tests: `backend/tests/test_inventory.py`

## Areas 5, 12: Reception Messages And Email Recipients

Owner paths: `backend/app/modules/communication/**`

Plan:
- Implement one daily message per `(date, user)`, HTML/plain content, history search, copy-to-today, comments and TXT export.
- Implement message email send as a queued notification/email intent using active recipients and configurable templates, without embedding SMTP secrets.

Tests: `backend/tests/test_communication.py`

## Area 6: Tasks And Calendar

Owner paths: `backend/app/modules/tasks/**`

Plan:
- Implement one-time and recurring tasks, weekly weekdays, interval recurrence, optional recurrence end date and occurrence-level completions.
- Provide day calendar and statistics endpoints.
- Deleting a recurring task deletes its occurrence completion rows.

Tests: `backend/tests/test_tasks.py`

## Area 7: Cash Diary And Shifts

Owner paths: `backend/app/modules/cash/**`

Plan:
- Implement shift log, cash diary upsert/edit/delete/history/export and automatic shift type detection from daily shift order.
- Calculate `difference = cash_end - cash_start`.
- Implement status checks for missing morning cash and missing evening cash after 20:00.

Tests: `backend/tests/test_cash.py`

## Areas 8, 9: Invoicing And Payments

Owner paths: `backend/app/modules/invoicing/**`

Plan:
- Implement atomic invoice counters, term validation, due date calculation, service/custom price validation, archive rows, payment states and manual paid/unpaid toggles.
- Generate a simple PDF file in configured storage and return `pdf_path`; keep PDF generation replaceable.
- Implement CSV export and overdue status refresh.

Tests: `backend/tests/test_invoicing.py`

## Area 10: Reporting

Owner paths: `backend/app/modules/reporting/**`

Plan:
- Implement read-only reports for invoices, tax summary and inventory monthly totals.
- Create export records for CSV/PDF/XLSX-like outputs under file storage.
- Do not mutate business records from reporting endpoints.

Tests: `backend/tests/test_reporting.py`

## Areas 11, 15: Backups, Recovery And Migration

Owner paths: `backend/app/modules/backups/**`, `backend/app/modules/migration/**`

Plan:
- Implement manual ZIP backups, retention-aware listing/deletion, recovery point snapshots and basic restore metadata.
- Implement housekeeping JSON migration from legacy `Komunikace pokojské/data.json` and photos folder into catalog/media/housekeeping-compatible data.
- Record migration results as audit-friendly import summaries.

Tests: `backend/tests/test_backups_migration.py`

## Area 13: Housekeeping

Owner paths: `backend/app/modules/housekeeping/**`

Plan:
- Implement assignments, status workflow, pause/resume duration, required photos, voluntary photos, minibar checklist uniqueness, history creation, revision tasks, laundry echo and monthly work report.
- Use `app.shared.files.save_upload` for photos and `app.shared.notifications.create_notification` for real-time-worthy workflow events.
- Keep housekeeping minibar checklist distinct from priced inventory minibar items.

Tests: `backend/tests/test_housekeeping.py`

## Area 14: Dashboard

Owner paths: `backend/app/modules/dashboard/**`

Plan:
- Implement an aggregate dashboard endpoint that reads module state through read-only queries.
- Include current user, today's message count, today's open task count, cash status, yesterday ending cash, invoice due warnings and housekeeping counters.

Tests: `backend/tests/test_dashboard.py`

