from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.defaults import DEFAULT_MODULES, DEFAULT_ROLES, DEFAULT_SETTINGS
from app.core.models import ModuleRegistry, Permission, Role, Setting, User
from app.core.security import hash_password


def bootstrap_core(db: Session, admin_password: str = "061004") -> None:
    roles: dict[str, Role] = {}
    for role_name, permission_codes in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name)
            db.add(role)
            db.flush()
        roles[role_name] = role

        for code in permission_codes:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=code)
                db.add(permission)
                db.flush()
            if permission not in role.permissions:
                role.permissions.append(permission)

    if db.scalar(select(User).where(User.username == "admin")) is None:
        db.add(
            User(
                username="admin",
                display_name="Administrátor",
                role_id=roles["admin"].id,
                password_hash=hash_password(admin_password),
                cannot_delete=True,
                comment_color="#ef4444",
            )
        )

    if db.get(Setting, "app") is None:
        db.add(Setting(key="app", value_json=DEFAULT_SETTINGS))

    for sort_order, (code, name) in enumerate(DEFAULT_MODULES):
        if db.scalar(select(ModuleRegistry).where(ModuleRegistry.code == code)) is None:
            db.add(ModuleRegistry(code=code, name=name, sort_order=sort_order))

    db.commit()

