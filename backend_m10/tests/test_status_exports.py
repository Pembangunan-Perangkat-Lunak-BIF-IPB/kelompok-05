"""Pengujian kontrak status/ekspor lokal, tanpa menyentuh PostgreSQL produksi.
Jalankan dari folder backend: python -m pytest tests/test_status_exports.py -q
"""
from datetime import datetime, timezone
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Pengujian tidak memerlukan driver PostgreSQL atau file .env. Semua akses DB
# diarahkan ke SQLite sementara sehingga tidak mengubah varescape_db.
fake_database = types.ModuleType("database")
fake_database.Base = declarative_base()
fake_database.get_db = lambda: None
sys.modules["database"] = fake_database
fake_security = types.ModuleType("security")
fake_security.require_researcher = lambda: None
sys.modules["security"] = fake_security
fake_pipeline = types.ModuleType("utils.pipeline")
fake_pipeline.run_analysis_pipeline = lambda _run_id: None
sys.modules["utils.pipeline"] = fake_pipeline

import models
from database import get_db
from routers import analysis
from security import require_researcher


@pytest.fixture
def service(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    now = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)
    session.add(models.User(
        id=1, email="test@example.invalid", hashed_password="not-for-login",
        role=models.UserRole.RESEARCHER, status_aktif=models.UserStatus.ACTIVE,
    ))
    session.add(models.AnalysisRun(
        run_id="VE-TEST-001", user_id=1, sample_name="Sample simulasi",
        status=models.RunStatus.COMPLETED, visibility=models.VisibilityType.PRIVATE,
        created_at=now, started_at=now, completed_at=now,
    ))
    session.add(models.PipelineLog(
        run_id="VE-TEST-001", station_number=1, log_level="SUCCESS",
        message="Stasiun uji selesai", created_at=now,
    ))
    session.add(models.VariantResult(
        run_id="VE-TEST-001", position=1, ref_allele="A", alt_allele="G",
        snpeff_effect='=HYPERLINK("example.invalid")',
        grantham_score=None, risk_level=None,
    ))
    session.commit()

    app = FastAPI()
    app.include_router(analysis.router)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_researcher] = lambda: 1
    monkeypatch.setattr(analysis, "UPLOAD_DIR", tmp_path)

    with TestClient(app) as client:
        yield client, session, app
    session.close()
    engine.dispose()


def test_uc07_status_contains_timestamps_and_station_logs(service):
    client, _, _ = service
    data = client.get("/api/v1/analysis/VE-TEST-001/status").json()
    assert data["overall_status"] == "COMPLETED"
    assert all(data[key] for key in ("created_at", "started_at", "completed_at"))
    assert data["pipeline_logs"][0]["station_number"] == 1
    assert data["pipeline_logs"][0]["created_at"].startswith("2026-11-07")
    assert data["pipeline_logs"][0]["timestamp"] == "08:00:00"
    assert len(data["stations"]) == 5


def test_csv_tsv_escape_formula_and_preserve_missing_value(service):
    client, _, _ = service
    for kind in ("csv", "tsv"):
        result = client.get(f"/api/v1/analysis/VE-TEST-001/export/{kind}")
        assert result.status_code == 200, result.text
        assert "attachment" in result.headers["content-disposition"]
        assert "'=HYPERLINK" in result.text
        assert "grantham_score" in result.text
        assert "None" not in result.text
        assert "," in result.text if kind == "csv" else "\t" in result.text


def test_logs_and_sanitized_configuration(service):
    client, _, _ = service
    logs = client.get("/api/v1/analysis/VE-TEST-001/export/logs")
    assert logs.status_code == 200
    assert "Stasiun uji selesai" in logs.text
    config = client.get("/api/v1/analysis/VE-TEST-001/export/config")
    assert config.status_code == 200
    assert config.json()["configuration_scope"] == "current_backend_settings_not_historical_run_snapshot"
    assert "DB_PASSWORD" not in config.text
    assert "SECRET_KEY" not in config.text


def test_private_export_denied_for_other_user(service):
    client, _, app = service
    app.dependency_overrides[require_researcher] = lambda: 2
    result = client.get("/api/v1/analysis/VE-TEST-001/export/csv")
    assert result.status_code == 403


def test_export_when_missing_and_unknown_format(service):
    client, _, _ = service
    assert client.get("/api/v1/analysis/VE-TEST-001/export/vcf").status_code == 404
    assert client.get("/api/v1/analysis/VE-TEST-001/export/foo").status_code == 400


def test_exports_require_completed_run(service):
    client, db, _ = service
    run = db.get(models.AnalysisRun, "VE-TEST-001")
    run.status = models.RunStatus.FAILED
    db.commit()
    assert client.get("/api/v1/analysis/VE-TEST-001/export/csv").status_code == 409
    assert client.get("/api/v1/analysis/VE-TEST-001/export/logs").status_code == 200
