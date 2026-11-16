"""Generate an owner/public PDF summary from persisted VarEscape run and variants."""
import io
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def _value(x):
    if x is None or x == "":
        return "-"
    return str(getattr(x, "value", x))


def build_analysis_pdf(run, variants):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=42, rightMargin=42,
                            topMargin=42, bottomMargin=42,
                            title=f"VarEscape - {run.run_id}")
    st = getSampleStyleSheet()
    story = [Paragraph("VarEscape | Laporan Variant Calling", st["Title"]), Spacer(1, 10)]
    fields = [
        ("Run ID", run.run_id), ("Sampel", run.sample_name),
        ("Status", run.status), ("Referensi", "NC_045512.2"),
        ("Mode", run.execution_mode), ("Dibuat", run.created_at),
        ("Q20 (%)", run.q20_rate), ("Q30 (%)", run.q30_rate),
        ("Mapping (%)", run.mapping_rate), ("Mean depth", run.mean_depth),
        ("Raw variants", run.raw_variant_count), ("PASS variants", run.passed_variant_count),
        ("Filtered variants", run.filtered_variant_count),
        ("Annotated variants", run.annotated_variant_count),
        ("Annotation status", run.annotation_status),
    ]
    def safe(t):
        return Paragraph(escape(_value(t)), st["BodyText"])
    table = Table([[safe(a),safe(b)] for a,b in fields], colWidths=[155, 345], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [colors.whitesmoke, colors.white]),
        ("VALIGN", (0,0),(-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING", (0,0),(-1,-1), 7),
    ]))
    story += [table, Spacer(1, 18), Paragraph("Parameter eksekusi", st["Heading2"])]
    params = [("min_dp",run.min_dp),("min_mq",run.min_mq),
              ("min_base_quality",run.min_base_quality),("max_depth",run.max_depth),
              ("min_qual",run.min_qual),("min_af",run.min_af)]
    story.append(Paragraph(" | ".join(f"{k}: {_value(v)}" for k,v in params), st["BodyText"]))
    story += [Spacer(1, 16), Paragraph("Daftar varian teranotasi", st["Heading2"])]
    story.append(Paragraph("Data berasal dari hasil tersimpan; tanda '-' berarti tidak tersedia.", st["BodyText"]))
    headers=["POS","REF","ALT","GENE","EFFECT","IMPACT"]
    rows=[[safe(h) for h in headers]]
    for v in variants:
        rows.append([safe(getattr(v,k,None)) for k in (
            'position','ref_allele','alt_allele','gene_name','snpeff_effect','impact')])
    if len(rows) == 1:
        rows.append([safe("Tidak ada varian")] + [safe("") for _ in range(5)])
    table2=Table(rows, colWidths=[47,48,48,76,184,78], repeatRows=1, hAlign="LEFT")
    table2.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfeeed')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.grey),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.whitesmoke]),
        ('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(table2)
    doc.build(story)
    return buf.getvalue()
