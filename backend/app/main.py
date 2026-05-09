from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.router import router as core_router
from app.modules.backups.router import router as backups_router
from app.modules.cash.router import router as cash_router
from app.modules.catalog.router import router as catalog_router
from app.modules.communication.router import router as communication_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.housekeeping.router import router as housekeeping_router
from app.modules.inventory.router import router as inventory_router
from app.modules.invoicing.router import router as invoicing_router
from app.modules.migration.router import router as migration_router
from app.modules.reporting.router import router as reporting_router
from app.modules.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="HEM API", version="0.1.0")
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "hem"}

    app.include_router(core_router)
    app.include_router(catalog_router)
    app.include_router(inventory_router)
    app.include_router(communication_router)
    app.include_router(tasks_router)
    app.include_router(cash_router)
    app.include_router(invoicing_router)
    app.include_router(reporting_router)
    app.include_router(housekeeping_router)
    app.include_router(dashboard_router)
    app.include_router(backups_router)
    app.include_router(migration_router)

    return app


app = create_app()
