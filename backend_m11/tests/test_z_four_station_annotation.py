"""Regression tests for the four-station, annotation-only data layer."""
from pathlib import Path
from types import SimpleNamespace

from utils.serializers import STATIONS, serialize_variant, safe_assessment_values
from utils.vcf_parser import parse_snpeff_ann, parse_info


def test_four_stations_and_annotation_terminal():
    assert len(STATIONS) == 4
    assert "SnpEff" in STATIONS[-1][1]
    assert not any("Epitope" in label or "Grantham" in label for _, label in STATIONS)


def test_variant_response_is_annotation_only():
    var = SimpleNamespace(id=1, run_id="VE-TEST", position=4, ref_allele="A",
                          alt_allele="G", qual=40.0, dp=18,
                          snpeff_effect="example annotation", grantham_score=90,
                          risk_level="HIGH")
    resp = serialize_variant(var)
    assert resp["annotation_status"] == "PRESENT"
    assert "risk_level" not in resp
    assert "grantham_score" not in resp


def test_no_annotation_gracefully_reported():
    var = SimpleNamespace(snpeff_effect=None)
    assert safe_assessment_values(var)["annotation_status"] == "UNAVAILABLE"
