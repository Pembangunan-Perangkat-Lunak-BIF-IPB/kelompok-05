"""Endpoint Administrator VarEscape.

Hanya akun ADMIN + ACTIVE yang boleh menggunakan router ini.
Tidak mengembalikan password, token, maupun rincian koneksi database.
"""

import os
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

import models
from config import UPLOAD_DIR
from database import get_db
from schemas.admin import AccountStatusUpdate
from security import require_admin

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administrator"],
    dependencies=[Depends(require_admin)],
)


def _enum_value(value):
    return getattr(value, "value", value)


def _account_payload(user: models.User) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": profile.full_name if profile else user.email,
        "institution": profile.institution if profile else None,
        # Kompatibilitas UI Accounts.jsx: roleOf(u) mencari string "READ".
        # Role asli di DB tetap PUBLIC, tersedia di account_role.
        "role": "READER" if user.role == models.UserRole.PUBLIC else _enum_value(user.role),
        "account_role": _enum_value(user.role),
        "status_aktif": _enum_value(user.status_aktif),
        "created_at": user.created_at,
    }


@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    """Data yang dibutuhkan tabel Accounts.jsx; akun administrator tidak dapat dikelola di sini."""
    users = (
        db.query(models.User)
        .options(joinedload(models.User.profile))
        .filter(models.User.role != models.UserRole.ADMIN)
        .order_by(models.User.created_at.desc(), models.User.id.desc())
        .all()
    )
    return [_account_payload(user) for user in users]


@router.patch("/accounts/{user_id}/status")
def change_account_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")
    if user.role == models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Status akun Administrator tidak dapat diubah lewat endpoint ini")

    old = user.status_aktif
    new = models.UserStatus(payload.status_aktif)
    if old == new:
        return _account_payload(user)  # aman bila permintaan diulang

    # Alur yang benar-benar disediakan oleh UI:
    # PENDING -> ACTIVE/REJECTED; ACTIVE -> SUSPENDED; SUSPENDED -> ACTIVE
    allowed = {
        models.UserStatus.PENDING_APPROVAL: {models.UserStatus.ACTIVE, models.UserStatus.REJECTED},
        models.UserStatus.ACTIVE: {models.UserStatus.SUSPENDED},
        models.UserStatus.SUSPENDED: {models.UserStatus.ACTIVE},
        models.UserStatus.REJECTED: set(),
    }
    if new not in allowed[old]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Perubahan status {_enum_value(old)} ke {_enum_value(new)} tidak diizinkan",
        )

    user.status_aktif = new
    db.commit()
    db.refresh(user)
    return _account_payload(user)


@router.post("/accounts/{user_id}/reset-password")
def reset_account_password(user_id: int, db: Session = Depends(get_db)):
    """Belum diaktifkan: reset memerlukan kanal verifikasi dan token sekali pakai."""
    user = db.get(models.User, user_id)
    if user is None or user.role == models.UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Reset password belum diaktifkan. Diperlukan pengiriman tautan verifikasi yang aman.",
    )


def _ram_info():
    """RAM yang terlihat dari proses Linux/WSL, bukan total RAM komputer Windows."""
    try:
        values = {}
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                label, _, value = line.partition(":")
                if label in {"MemTotal", "MemAvailable"}:
                    values[label] = int(value.strip().split()[0]) * 1024
        total, available = values["MemTotal"], values["MemAvailable"]
        if total <= 0:
            return {}
        used = total - available
        return {
            "ram_percent": round(100 * used / total, 1),
            "ram_used_gb": round(used / 1024**3, 2),
            "ram_total_gb": round(total / 1024**3, 2),
        }
    except (OSError, ValueError, KeyError):
        return {}


def _disk_info():
    try:
        path = UPLOAD_DIR if UPLOAD_DIR.exists() else UPLOAD_DIR.parent
        total, used, _free = shutil.disk_usage(path)
        if total <= 0:
            return {}
        return {
            "disk_percent": round(100 * used / total, 1),
            "disk_used_gb": round(used / 1024**3, 2),
            "disk_total_gb": round(total / 1024**3, 2),
        }
    except (OSError, ValueError):
        return {}


def _elapsed_string(run: models.AnalysisRun):
    started = run.started_at or run.created_at
    if not started:
        return None
    if started.tzinfo is None:
        # timestamp tanpa timezone: tidak membuat asumsi durasi yang bisa keliru
        return None
    minutes = max(0, int((datetime.now(timezone.utc) - started).total_seconds() // 60))
    return f"{minutes} menit"


@router.get("/health")
def get_admin_health(db: Session = Depends(get_db)):
    """Telemetri host lokal yang benar-benar tersedia; lainnya null, bukan angka palsu."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database tidak dapat dihubungi")

    runs = (
        db.query(models.AnalysisRun)
        .options(joinedload(models.AnalysisRun.user))
        .filter(models.AnalysisRun.status.in_([models.RunStatus.PENDING, models.RunStatus.RUNNING]))
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(50)
        .all()
    )
    queue = [
        {
            "run_id": run.run_id,
            "owner": run.user.email if run.user else None,
            "stage": None,  # status stasiun tidak diambil dari scheduler HPC
            "alloc": None,
            "elapsed": _elapsed_string(run),
            "status": _enum_value(run.status),
        }
        for run in runs
    ]

    return {
        "status": "ok",
        "database": "connected",
        "node_id": platform.node(),
        "cpu_cores": os.cpu_count(),
        "cpu_percent": None,  # tidak mengklaim load average sebagai utilisasi CPU
        "cpu_cores_active": None,
        "pipeline_engine": "FastAPI BackgroundTasks",
        "daemon_status": None,
        "tools": None,
        "io_write": None,
        "io_read": None,
        "temperature_c": None,
        "queue": queue,  # run PENDING/RUNNING di DB, bukan antrean scheduler HPC
        **_ram_info(),
        **_disk_info(),
    }
