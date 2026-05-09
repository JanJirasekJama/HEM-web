from pathlib import Path


def test_reporting_and_dashboard_do_not_import_private_business_models() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "modules"
    forbidden = [
        "app.modules.inventory.models",
        "app.modules.invoicing.models",
        "app.modules.communication.models",
        "app.modules.tasks.models",
        "app.modules.cash.models",
        "app.modules.housekeeping.models",
    ]

    for module in ["reporting", "dashboard"]:
        source = "\n".join(path.read_text(encoding="utf-8") for path in (root / module).glob("*.py"))
        for import_path in forbidden:
            assert import_path not in source
