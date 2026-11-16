"""Unit checks without starting live PostgreSQL or running sequencing tools."""
import sys, types
from sqlalchemy.orm import declarative_base
if "database" not in sys.modules:
    fake_db = types.ModuleType("database")
    fake_db.Base = declarative_base()
    sys.modules["database"] = fake_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, AnalysisRun, User, UserRole, UserStatus, ExecutionMode
from utils.vcf_parser import filter_vcf, parse_snpeff_ann
from utils.genomics import evaluate_variant


def test_four_station_schema_and_custom_params():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add(User(id=1,email="local@example.invalid",hashed_password="placeholder",role=UserRole.RESEARCHER,status_aktif=UserStatus.ACTIVE))
        db.add(AnalysisRun(run_id="VE-TEST", user_id=1, sample_name="unit", execution_mode=ExecutionMode.CUSTOM, min_dp=15, min_mq=20, min_qual=40, min_af=0.15))
        db.commit()
        run = db.get(AnalysisRun, "VE-TEST")
        assert run.min_dp == 15 and run.min_af == 0.15
        assert "grantham_score" not in Base.metadata.tables["variant_results"].c
        assert len(Base.metadata.tables) == 6


def test_filter_uses_custom_threshold_and_missing_field_is_not_pass(tmp_path):
    inp=tmp_path/"raw.vcf"
    out=tmp_path/"filtered.vcf"
    inp.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nNC_045512.2\t5\t.\tA\tG\t50\tPASS\tDP=20;MQ=40;AF=0.4\nNC_045512.2\t6\t.\tC\tT\t50\tPASS\tDP=20;AF=0.4\n")
    assert filter_vcf(str(inp),str(out),{"dp":15,"mq":30,"qual":30,"af":0.2})==(2,1)
    assert "\t5\t" in out.read_text() and "\t6\t" not in out.read_text()
    assert evaluate_variant(dp=20,mq=None,qual=50,af=0.4)[0] is False
