from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from smart_legal_platform.config import get_settings
from smart_legal_platform.security import decrypt_text, encrypt_text
from smart_legal_platform.store import store


def _serialize_store() -> dict:
    return {
        "cases": {key: value.model_dump(mode="json") for key, value in store.cases.items()},
        "tasks": {key: [item.model_dump(mode="json") for item in value] for key, value in store.tasks.items()},
        "appointments": {
            key: [item.model_dump(mode="json") for item in value]
            for key, value in store.appointments.items()
        },
        "time_entries": {
            key: [item.model_dump(mode="json") for item in value]
            for key, value in store.time_entries.items()
        },
        "invoices": {
            key: [item.model_dump(mode="json") for item in value]
            for key, value in store.invoices.items()
        },
        "messages": [msg.model_dump(mode="json") for msg in store.messages],
        "signatures": [sig.model_dump(mode="json") for sig in store.signatures],
    }


def create_backup() -> str:
    settings = get_settings()
    backup_dir = Path(settings.cloud_backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"backup-{timestamp}.json.enc"
    path = backup_dir / filename

    serialized = json.dumps(_serialize_store(), ensure_ascii=True)
    encrypted_payload = encrypt_text(serialized)
    path.write_text(encrypted_payload, encoding="utf-8")
    return str(path)


def read_latest_backup() -> dict:
    settings = get_settings()
    backup_dir = Path(settings.cloud_backup_dir)
    if not backup_dir.exists():
        raise HTTPException(status_code=404, detail="No backups available")
    backups = sorted(backup_dir.glob("backup-*.json.enc"), reverse=True)
    if not backups:
        raise HTTPException(status_code=404, detail="No backups available")
    encrypted_payload = backups[0].read_text(encoding="utf-8")
    payload = decrypt_text(encrypted_payload)
    return json.loads(payload)

