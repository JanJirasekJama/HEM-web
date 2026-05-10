"""Read-only query contracts for housekeeping-owned data."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.housekeeping.models import HousekeepingAssignment, LaundryTask, RevisionTask


def get_housekeeping_dashboard_status(db: Session) -> dict[str, int]:
    rows = db.execute(select(HousekeepingAssignment.status, func.count()).group_by(HousekeepingAssignment.status)).all()
    by_status = {str(status): int(count) for status, count in rows}
    return {
        "waiting": sum(by_status.get(status, 0) for status in ["Prideleno", "Ceka", "waiting"]),
        "cleaning": sum(by_status.get(status, 0) for status in ["Uklizi se", "cleaning"]),
        "done": sum(by_status.get(status, 0) for status in ["Hotovo", "done"]),
        "laundry_active": int(db.scalar(select(func.count()).select_from(LaundryTask).where(LaundryTask.status.in_(["open", "accepted"]))) or 0),
        "open_revisions": int(db.scalar(select(func.count()).select_from(RevisionTask).where(RevisionTask.status == "open")) or 0),
    }
