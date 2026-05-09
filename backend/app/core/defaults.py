DEFAULT_ROLES = {
    "admin": ["*"],
    "recepcni": [
        "messages:*",
        "tasks:*",
        "cash:*",
        "inventory:*",
        "invoices:*",
        "housekeeping:reception",
    ],
    "ucetni": ["invoices:*", "reports:*", "exports:*"],
    "pokojska": ["housekeeping:work", "notifications:read"],
}

DEFAULT_SETTINGS = {
    "company": {
        "name": "Wellness Hotel Beethoven",
        "address": "Beethovenova 1146, 430 01 Chomutov",
        "company_id": "",
        "company_vat": "",
        "branch_name": "",
        "branch_address": "",
        "num_rooms": 30,
    },
    "ui": {"theme": "system", "language": "cs"},
    "finance": {"currency": "CZK", "tax_rate": 21, "open_pdf_after_create": True},
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "",
        "password_secret_ref": "",
        "sender": "recepce@hotelbeethoven.cz",
        "message_subject_template": "Vzkazy z recepce - {date}",
        "message_body_template": "{messages}",
        "invoice_body_template": "Dobrý den, v příloze posíláme zálohovou fakturu.",
    },
    "backup": {"enabled": True, "path": "/data/files/backups", "interval_days": 7, "keep_days": 10, "versions_to_keep": 10},
    "housekeeping": {
        "photo_max_mb": 6,
        "allowed_photo_types": ["image/jpeg", "image/png", "image/webp"],
        "require_laundry_photo": True,
        "default_work_types": ["Prijezd", "Odjezd", "Prubeh", "Jine ukoly"],
        "default_priorities": ["Normalni", "Vysoka", "Nizka"],
    },
    "realtime": {"enabled": True, "transport": "sse", "poll_fallback_seconds": 2},
    "pwa": {"enabled": True, "installable": True, "offline_fallback": True, "asset_cache_strategy": "stale-while-revalidate", "push_notifications": True},
    "modules": {
        "inventory": True,
        "communication": True,
        "tasks": True,
        "cash_diary": True,
        "invoicing": True,
        "housekeeping": True,
        "reporting": True,
    },
    "deployment": {"runtime": "docker-compose", "database": "postgresql", "file_storage_root": "/data/files", "public_base_url": ""},
}

DEFAULT_MODULES = [
    ("core", "Jádro"),
    ("inventory", "Inventory"),
    ("communication", "Vzkazy"),
    ("tasks", "Úkoly"),
    ("cash_diary", "Peněžní deník"),
    ("invoicing", "Fakturace"),
    ("reporting", "Reporty"),
    ("housekeeping", "Housekeeping"),
    ("notifications", "Notifikace"),
    ("files", "Soubory"),
    ("backups", "Zálohy"),
    ("migration", "Migrace"),
]

