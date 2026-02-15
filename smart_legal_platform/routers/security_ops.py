from __future__ import annotations

from fastapi import APIRouter, Depends

from smart_legal_platform.models import User
from smart_legal_platform.security import require_permission
from smart_legal_platform.services.backup_service import create_backup, read_latest_backup


router = APIRouter(prefix="/api/security", tags=["security"])


@router.post("/backup")
def backup(_: User = Depends(require_permission("backup:run"))) -> dict[str, str]:
    backup_path = create_backup()
    return {"backup_path": backup_path}


@router.get("/backup/latest")
def latest_backup(_: User = Depends(require_permission("backup:run"))) -> dict:
    return read_latest_backup()

