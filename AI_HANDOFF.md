# AI_HANDOFF.md - HEM konsolidace

Aktualizovano: 2026-05-11.

Tento soubor je novy technicky handoff po auditu rozdelaneho projektu. Predchozi commitovana verze `AI_HANDOFF.md` byla obecny "resume po timeoutu" dokument; v aktualnim pracovnim stromu byla vymazana na 0 radku. Tento dokument ji nahrazuje presnym stavem projektu.

## Nejdulezitejsi stav

- Vetev: `main`, HEAD pri auditu `64b0fd4 Add local start wrapper`, `main` byla shodna s `origin/main`.
- Dirty worktree pri auditu: `M AI_HANDOFF.md`, `?? COMMAND.md`.
- `COMMAND.md` je user prompt/context, nemenit ani necommitovat bez vedomeho rozhodnuti.
- Nezacinat od nuly. Repo uz ma implementovany backend, frontend integraci, Docker stack, migrace, testy a lokalni start wrapper.
- Overeni testu v tomto behu neprobehlo, protoze v prostredi nejsou dostupne `uv` ani `npm` (`bash: uv: command not found`, `bash: npm: command not found`).

## Zdrojove artefakty

- Requirements: `HEM_konsolidace_requirements.md`.
- Legacy desktop zdroje: `HEM-comunicate.py`, `HEM-inventory.py`, `HEM_Lite_zalohy (3).py`.
- Legacy web housekeeping: `Komunikace pokojské/` vcetne `server.js`, `app.js`, `data.json`, `photos/`.
- Subagent plany: `docs/subagent_plans.md`.
- Aktualni aplikace: `backend/`, `frontend/`, `docker-compose.yml`, `run-local.sh`, `scripts/run-linux-test.sh`.

## Co je hotove

Backend je funkcni modularni FastAPI monolit se SQLAlchemy, Alembic, Docker Compose stackem a testy pro hlavni domeny.

- `backend/app/main.py` zapojuje moduly `core`, `catalog`, `inventory`, `communication`, `tasks`, `cash`, `invoicing`, `reporting`, `housekeeping`, `dashboard`, `backups`, `migration`.
- `docker-compose.yml` obsahuje `frontend`, `backend`, `postgres`, `redis` a persistentni volumes.
- `backend/scripts/start.sh` spousti migrace a seed.
- Auth/core ma session cookie, CSRF, role, permissions, Argon2 hash, rehash legacy hesel, zakaz smazani chraneneho admina a self-delete.
- Katalogy pokryvaji sluzby, splatnosti, inventory polozky, pokoje, foto typy, housekeeping minibar a e-mail prijemce.
- Inventory umi denni zaznamy pro wellness/minibar/lobby, archiv, editaci, custom lobby radky a mesicni JSON agregace.
- Komunikace umi denni vzkazy, historii, komentare create, copy-to-today, TXT export a e-mail intent.
- Ukoly umi create, kalendar, recurring weekly/interval, completion per occurrence a delete.
- Cash umi shift log, denik, historii zmen, CSV export a status chybejici hotovosti.
- Fakturace umi vytvoreni zalohove faktury, validaci terminu, splatnost, cislo/VS, PDF, archiv, payment status, CSV export a e-mail intent.
- Reporting umi fakturacni statistiky, danovy report a inventory monthly read model.
- Housekeeping umi assignment workflow, required photos, upload validaci, minibar checklist uniqueness, historii, revize, pradelnu a monthly work report.
- Backups/recovery umi manual ZIP snapshot DB + files, seznam/smazani a recovery point restore.
- Migration umi import housekeeping JSON/fotek a cast legacy suite.
- Dashboard agreguje uzivatele, vzkazy, ukoly, cash, faktury a housekeeping counters.

Frontend je integrovany React/Vite/Tailwind/shadcn-style shell:

- `frontend/src/App.tsx` je cisty composition root (`AppStateProvider` + `DashboardShell`).
- `frontend/src/shared/auth/AppState.tsx` centralizuje auth, dashboard, permissions, refresh, notifikace a SSE polling.
- `frontend/src/features/modules.ts` registruje moduly a permission gating.
- Existuji workspace/panely pro admin, finance/reporting, housekeeping, operations panely.
- PWA shell existuje: `manifest.webmanifest`, `service-worker.js`, `offline.html`, registrace v `main.tsx`.
- UI primitives jsou v `frontend/src/components/ui` a `components.json` ma aliasy pro shadcn/ui.

## Testy a overeni

Existujici test coverage:

- Backend API testy: `backend/tests/test_core.py`, `test_authorization.py`, `test_architecture.py`, `test_catalogs.py`, `test_inventory.py`, `test_communication.py`, `test_tasks.py`, `test_cash.py`, `test_invoicing.py`, `test_reporting.py`, `test_housekeeping.py`, `test_dashboard.py`, `test_backups_restore.py`, `test_backups_migration.py`.
- Frontend testy: `frontend/src/test/api.test.ts`, `permissions.test.ts`, `pwa.test.ts`, `module-outlet.test.tsx`, `frontend/src/features/housekeeping/HousekeepingWorkspace.test.tsx`.

V tomto auditu neslo spustit:

```bash
cd backend && uv run pytest
cd frontend && npm test
cd frontend && npm run build
cd frontend && npm run lint
```

Duvod: lokalni prostredi ma `python3` a `podman`, ale nema `uv`, `npm`, `node`.

Prvni krok dalsiho agenta po zprovozneni toolchainu:

```bash
cd backend && uv sync --dev && uv run pytest
cd frontend && npm install && npm test && npm run build && npm run lint
./run-local.sh
```

## Hlavni gapy proti requirements

P0/P1 oblasti, ktere brani prohlaseni projektu za hotovy:

1. E-mail: backend jen uklada/vraci e-mail intent (`queued` / `persisted_intent`), chybi realne SMTP odesilani a worker.
2. Real-time/notifikace: Redis queue existuje, ale `/api/events` posila jen `ready` a `ping`; chybi fan-out domenovych udalosti do SSE, push subscriptions API/UI a notification preferences.
3. Background jobs: chybi scheduler/worker pro automaticke zalohy, overdue refresh, cash reminders, e-mail delivery a push delivery.
4. Files/photo serving: upload a `MediaFile` existuji, ale chybi endpoint pro bezpecne servirovani `/api/files/...`; housekeeping fotky nemaji pouzitelne public URL.
5. Housekeeping parity: chybi recepcni edit/return/delete/check/archive assignmentu, detail historie s velkymi fotkami, edit/delete historie, dodatkove prace v pokoji i mimo pokoj, laundry cancel, samostatny HK minibar monthly report a PDF export.
6. Vzkazy: chybi edit/delete komentaru, delete historickeho vzkazu, detail historie vcetne komentaru a frontend formulare pro snidane/prijezdy/odjezdy/prubehy/wellness counts do e-mailu.
7. Ukoly: chybi editace ukolu v backendu i frontendu.
8. Reporting/exporty: `/api/reports/exports` je spis placeholder; chybi plnohodnotne CSV/PDF/XLSX pro faktury, dane, inventory a housekeeping reporty.
9. Zaloha/retence/integrita: rucni zalohy jsou, ale chybi automaticke zalohy podle nastaveni, retence scheduler a hash/integrity kontrola.
10. Secrets: settings porad mohou obsahovat SMTP `password` v JSON; requirements chce tajemstvi mimo DB, idealne `password_secret_ref`/env/secrets.
11. Audit log: model existuje, ale hlavni business mutace do nej systematicky nezapisuji.
12. Alembic: `0001_initial_schema.py` pouziva `Base.metadata.create_all/drop_all`, coz neni vhodna auditovatelna produkcni migrace.
13. Invoice numbering: counter je lepsi nez max+1, ale je potreba overit/zesilit PostgreSQL soubeh explicitnim lockem/testem.
14. Frontend API vrstva: fetch/CSRF/abort logika je duplicitni v `shared/api.ts`, `operations/api.ts`, `finance/api.ts`, `admin/api.ts`, `housekeeping/hooks.ts`.
15. Admin UX: settings jsou JSON editor, ne bezpecne formulare pro firmu, SMTP, zalohy, notifikace a tajemstvi; destructive akce potrebuji confirm dialogy.
16. PWA: instalovatelny/offline shell existuje, ale neni offline queue ani jasne modulove offline chovani.

## Frontend konkretni rizika

- `OperationsWorkspace` je pravdepodobne legacy/duplicitni agregator; hlavni navigace pouziva primo panely z `modules.ts`.
- `frontend/src/features/notifications/useNotifications.ts` je duplicitni/nepouzity vedle notifikaci v `AppStateProvider`.
- `HousekeepingWorkspace` ma nejkompletnejsi UX, ale soubor je velky a cast logiky by mela zustat v hookach/helper vrstvach.
- `housekeeping/hooks.ts` nacita CSRF token jen jednou; po zmene session hrozi stale token.
- `useFinanceResource` a `useAdminResource` nemaji robustni abort/race handling pro manualni reloady.
- Login ma default username `admin`, vhodne pro dev, nevhodne pro produkci.

## Doporuceny plan pokracovani

Pracovat TDD a zero-trust stylem. Pro kazdou oblast nejdrive doplnit testy, pak predat implementaci workerovi, nasledne audit subagentovi. Nepovolovat workerum menit testy bez explicitniho souhlasu orchestratora.

1. Zprovoznit toolchain a spustit cele testy/build/lint. Bez toho nedelat velke refaktory.
2. Stabilizovat backend infrastrukturu:
   - explicitni Alembic migrace,
   - file serving endpoint + authorization,
   - audit log helper,
   - Redis/SSE real event bridge,
   - background worker/scheduler.
3. Dodelat provozni delivery:
   - SMTP worker pro message/invoice intents,
   - notification preferences/push fallback,
   - automatic backups/retention,
   - invoice overdue/cash reminders.
4. Dodelat housekeeping parity backlog, protoze je nejvetsi business gap proti `Komunikace pokojské/`.
5. Dodelat communication/tasks parity: message/comment CRUD, message detail, e-mail counts UI, task edit.
6. Dodelat reporting/exporty: skutecne CSV/PDF/XLSX a HK minibar report.
7. Sjednotit frontend API klienta, CSRF a abort handling; potom cistit duplicity (`OperationsWorkspace`, `useNotifications`).
8. Zlepsit admin/finance UX: potvrzovaci dialogy, normalni settings formulare, delete invoice UI, dashboard drilldowns.
9. Rozsirit migraci legacy dat o komentare, shift log, invoice PDF originaly a kompletni HK nuance.

## Modulova mapa pro dalsi agenty

- Core/auth/settings: `backend/app/core/**`, `backend/tests/test_core.py`, `test_authorization.py`; frontend `frontend/src/shared/auth/**`, `frontend/src/features/admin/UserRolesPanel.tsx`.
- Catalogs: `backend/app/modules/catalog/**`, `backend/tests/test_catalogs.py`; frontend `frontend/src/features/admin/AdminWorkspace.tsx`.
- Inventory: `backend/app/modules/inventory/**`, `backend/tests/test_inventory.py`; frontend `frontend/src/features/operations/components/InventoryPanel.tsx`.
- Communication: `backend/app/modules/communication/**`, `backend/tests/test_communication.py`; frontend `MessagesPanel.tsx`.
- Tasks: `backend/app/modules/tasks/**`, `backend/tests/test_tasks.py`; frontend `TasksPanel.tsx`.
- Cash: `backend/app/modules/cash/**`, `backend/tests/test_cash.py`; frontend `CashPanel.tsx`.
- Invoicing: `backend/app/modules/invoicing/**`, `backend/tests/test_invoicing.py`; frontend `frontend/src/features/finance/**`.
- Reporting: `backend/app/modules/reporting/**`, `backend/tests/test_reporting.py`; frontend finance reports tab.
- Housekeeping: `backend/app/modules/housekeeping/**`, `backend/tests/test_housekeeping.py`; frontend `frontend/src/features/housekeeping/**`.
- Backups/recovery: `backend/app/modules/backups/**`, `backend/tests/test_backups_restore.py`; frontend admin backups tab.
- Migration: `backend/app/modules/migration/**`, `backend/tests/test_backups_migration.py`.
- Dashboard: `backend/app/modules/dashboard/**`, `backend/tests/test_dashboard.py`; frontend `DashboardOverview.tsx`.

## Zachazeni s gitem

- Neprovadet `git reset --hard` ani `git checkout --` na user changes.
- Pred commitem vzdy `git status --short --branch` a relevantni testy.
- Commitovat jen souvisejici zmeny. `COMMAND.md` je zatim untracked user context.
- `CODEX_STATUS*.txt`, `CODEX_DIFF_SUMMARY*.txt`, `CODEX_PROGRESS*.patch` jsou historicke/diagnosticke soubory; necistit bez souhlasu.

## Kratky zaver

Projekt ma solidni kostru a hodne backend domen uz je prepsano test-first stylem. Neni ale hotovy jako produkcni nahrada vsech legacy aplikaci. Nejvetsi nedodelky jsou provozni infrastruktura (worker, SSE, e-mail, scheduler, secrets, audit), housekeeping parity, plnohodnotne exporty, automaticke zalohy a sjednoceni frontend API/UX.
