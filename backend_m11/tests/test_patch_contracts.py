from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_python_parse():
    for name in ("models.py", "routers/analysis.py", "utils/pipeline.py",
                 "utils/snpeff.py", "utils/report_generator.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"))

def test_cancel_and_partial_contract():
    models = (ROOT / "models.py").read_text()
    analysis = (ROOT / "routers/analysis.py").read_text()
    pipeline = (ROOT / "utils/pipeline.py").read_text()
    report = (ROOT / "utils/report_generator.py").read_text()
    assert 'CANCELLED = "CANCELLED"' in models
    assert '@router.post("/{run_id}/cancel"' in analysis
    assert '"summary_metrics": summary_metrics' in analysis
    assert '_require_terminal_with_artifact(run, run_id)' in analysis
    assert "PipelineCancelled" in pipeline
    assert "models.AnnotationStatus.SKIPPED" in pipeline
    assert 'run_status != \'COMPLETED\'' in report
