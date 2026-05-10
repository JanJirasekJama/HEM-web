from app.core.bootstrap import bootstrap_core
from app.core.database import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        bootstrap_core(db)


if __name__ == "__main__":
    main()

