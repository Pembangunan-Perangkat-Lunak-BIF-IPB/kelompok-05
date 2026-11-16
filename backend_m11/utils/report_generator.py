
"""VarEscape reporting: PDF generated from saved run metrics and artifacts.

No pipeline commands, invented metrics, or clinical/immune-escape inference.
Requires reportlab >= 4.2.
"""

from __future__ import annotations

from collections import Counter
from html import escape
from io import BytesIO
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)


DARK = colors.HexColor("#143449")
TEAL = colors.HexColor("#0D828A")
LIGHT = colors.HexColor("#E8F5F5")
MUTED = colors.HexColor("#526879")
GRAY = colors.HexColor("#EDF2F4")


def _s(value):
    if value is None or value == "":
        return "Tidak tersedia"
    return str(value)


def _num(value, digits=2, suffix=""):
    if value is None:
        return "Tidak tersedia"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return _s(value)


def _paragraph(value, style):
    return Paragraph(escape(_s(value)), style)


def _enum(value):
    return getattr(value, "value", value)


def _read_json_safe(path: Path):
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > 8_000_000
        ):
            return {}

        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}

    except (OSError, ValueError, UnicodeError):
        return {}


def _raw_vcf_statistics(path: Path):
    """Hitung statistik raw VCF tanpa menggunakan varian PASS saja."""
    if path.is_symlink() or not path.is_file():
        return None

    result = {
        "total": 0,
        "snp": 0,
        "indel": 0,
        "ts": 0,
        "tv": 0,
        "substitutions": Counter(),
    }

    transitions = {"AG", "GA", "CT", "TC"}

    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.startswith("#"):
                    continue

                columns = line.rstrip("\n").split("\t")
                if len(columns) < 5:
                    continue

                ref = columns[3].upper()
                alts = columns[4].upper().split(",")

                for alt in alts:
                    if not alt or alt == ".":
                        continue

                    result["total"] += 1

                    if (
                        len(ref) == 1
                        and len(alt) == 1
                        and ref in "ACGT"
                        and alt in "ACGT"
                        and ref != alt
                    ):
                        result["snp"] += 1
                        result["substitutions"][f"{ref}>{alt}"] += 1

                        if ref + alt in transitions:
                            result["ts"] += 1
                        else:
                            result["tv"] += 1

                    elif len(ref) != len(alt):
                        result["indel"] += 1

    except (OSError, UnicodeError):
        return None

    return result


class Bars(Flowable):
    """Grafik batang horizontal sederhana berbasis vektor."""

    def __init__(self, rows, width=166 * mm, title=None, unit=""):
        super().__init__()

        self.rows = [
            (str(label), float(value))
            for label, value in rows
            if value is not None and float(value) >= 0
        ]

        self.width = width
        self.height = (
            len(self.rows) * 12
            + (15 if title else 0)
            + 4
        ) * mm

        self.title = title
        self.unit = unit

    def draw(self):
        c = self.canv
        y = self.height

        if self.title:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(DARK)
            y -= 11 * mm
            c.drawString(0, y, self.title)

        maximum = max([value for _, value in self.rows] or [1])

        label_width = 46 * mm
        bar_width = self.width - 80 * mm

        for label, value in self.rows:
            y -= 11 * mm

            c.setFont("Helvetica", 8)
            c.setFillColor(DARK)
            c.drawString(0, y + 2, label[:35])

            c.setFillColor(GRAY)
            c.roundRect(
                label_width, y, bar_width, 6 * mm, 2 * mm,
                fill=1, stroke=0
            )

            if value > 0 and maximum > 0:
                c.setFillColor(TEAL)
                c.roundRect(
                    label_width,
                    y,
                    bar_width * value / maximum,
                    6 * mm,
                    2 * mm,
                    fill=1,
                    stroke=0,
                )

            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(
                label_width + bar_width + 3 * mm,
                y + 2,
                f"{value:g}{self.unit}",
            )


class GenomePlot(Flowable):
    """Distribusi posisi varian PASS sepanjang genom referensi."""

    def __init__(
        self,
        positions,
        width=165 * mm,
        ref_length=29903,
    ):
        super().__init__()

        self.positions = [
            int(pos)
            for pos in positions
            if pos is not None
            and 1 <= int(pos) <= ref_length
        ]

        self.width = width
        self.height = 29 * mm
        self.ref_length = ref_length

    def draw(self):
        c = self.canv
        width = self.width

        c.setStrokeColor(DARK)
        c.setLineWidth(1.5)
        c.line(7 * mm, 15 * mm, width - 7 * mm, 15 * mm)

        for pos in self.positions:
            x = (
                7 * mm
                + (width - 14 * mm)
                * (pos - 1)
                / (self.ref_length - 1)
            )

            c.setStrokeColor(TEAL)
            c.setLineWidth(0.6)
            c.line(x, 15 * mm, x, 22 * mm)

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)

        c.drawString(7 * mm, 8 * mm, "1 bp")
        c.drawRightString(
            width - 7 * mm,
            8 * mm,
            f"{self.ref_length:,} bp",
        )

        c.drawCentredString(
            width / 2,
            2 * mm,
            "Posisi varian PASS pada genom referensi",
        )


def generate_variant_report(
    run,
    variants,
    run_dir,
    station_interpretations=None,
    filter_audit=None,
):
    """Menghasilkan PDF dari data tersimpan tanpa menjalankan pipeline."""

    run_status = _enum(getattr(run, "status", None))

    if run_status not in {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }:
        raise ValueError(
            "PDF hanya tersedia untuk run terminal."
        )

    run_dir = Path(run_dir)

    coverage = _read_json_safe(
        run_dir / "coverage_metrics.json"
    )

    raw = _raw_vcf_statistics(
        run_dir / "variants.vcf"
    )

    variants = list(variants or [])

    impact_counts = Counter()
    effect_counts = Counter()

    for var in variants:
        impact = getattr(var, "impact", None)

        if impact:
            impact_counts[str(impact).upper()] += 1

        effect = None
        annotation = getattr(var, "annotation_raw", None)

        if annotation:
            first = str(annotation).split(",")[0].split("|")
            if len(first) > 1:
                effect = first[1].split("&")[0]

        if not effect:
            label = getattr(var, "snpeff_effect", None)
            if label and "(" in str(label):
                effect = str(label).rsplit("(", 1)[-1].rstrip(")")

        if effect:
            effect_counts[effect] += 1

    # ============================================================
    # STYLES
    # ============================================================

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="VTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=DARK,
        spaceAfter=9,
    ))

    styles.add(ParagraphStyle(
        name="VSub",
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=MUTED,
        spaceAfter=14,
    ))

    styles.add(ParagraphStyle(
        name="VHead",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=DARK,
        spaceBefore=13,
        spaceAfter=8,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="VText",
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=DARK,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="VSmall",
        fontName="Helvetica",
        fontSize=7.5,
        leading=11,
        textColor=MUTED,
        spaceAfter=7,
    ))

    styles.add(ParagraphStyle(
        name="VCell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=DARK,
    ))

    styles.add(ParagraphStyle(
        name="VAuditCell",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=DARK,
        wordWrap="CJK",
    ))

    styles.add(ParagraphStyle(
        name="VAuditHeader",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
    ))

    # ============================================================
    # DOCUMENT SETUP
    # ============================================================

    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=19 * mm,
        rightMargin=19 * mm,
        topMargin=22 * mm,
        bottomMargin=19 * mm,
        title=f"VarEscape - {run.run_id}",
        author="VarEscape",
    )

    def page_footer(canvas, document):
        canvas.saveState()

        canvas.setStrokeColor(
            colors.HexColor("#DDE7EA")
        )

        canvas.line(
            19 * mm, 16 * mm,
            191 * mm, 16 * mm,
        )

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)

        canvas.drawString(
            19 * mm,
            11 * mm,
            f"VarEscape | Run {_s(run.run_id)} | "
            "Variant calling & SnpEff",
        )

        canvas.drawRightString(
            191 * mm,
            11 * mm,
            f"Halaman {document.page}",
        )

        canvas.restoreState()

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    doc.addPageTemplates(
        PageTemplate(
            id="report",
            frames=[frame],
            onPage=page_footer,
        )
    )

    story = []

    P = lambda value: _paragraph(value, styles["VText"])
    H = lambda value: _paragraph(value, styles["VHead"])

    def table_pairs(items):
        rows = [
            [
                _paragraph(str(label), styles["VCell"]),
                _paragraph(str(value), styles["VCell"]),
            ]
            for label, value in items
        ]

        table = Table(
            rows,
            colWidths=[58 * mm, 110 * mm],
            hAlign="LEFT",
        )

        table.setStyle(TableStyle([
            (
                "ROWBACKGROUNDS",
                (0, 0), (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F4F8F8"),
                ],
            ),
            (
                "LINEBELOW",
                (0, 0), (-1, -1),
                0.25,
                colors.HexColor("#DDE7EA"),
            ),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        return table

    # ============================================================
    # COVER
    # ============================================================

    story.append(
        _paragraph("VarEscape", styles["VTitle"])
    )

    if run_status != "COMPLETED":
        story.append(_paragraph(
            f"LAPORAN PARSIAL - {run_status}. "
            "Hanya hasil stasiun yang sudah tersimpan. "
            "Tahap yang belum selesai tidak boleh "
            "diinterpretasikan sebagai hasil negatif.",
            styles["VSub"],
        ))
    else:
        story.append(_paragraph(
            "Laporan hasil variant calling dan "
            "anotasi genom SARS-CoV-2",
            styles["VSub"],
        ))

    reference_accession = (
        getattr(run, "reference_accession", None)
        or "NC_045512.2 "
           "(referensi sistem; identitas run belum direkam)"
    )

    story.append(table_pairs([
        ("Run ID", run.run_id),
        ("Sampel", run.sample_name),
        ("Status", _enum(run.status)),
        ("Genom acuan", reference_accession),
        (
            "SHA256 referensi",
            getattr(run, "reference_sha256", None),
        ),
        ("Mulai", getattr(run, "started_at", None)),
        ("Selesai", getattr(run, "completed_at", None)),
    ]))

    # ============================================================
    # 01 / RINGKASAN HASIL
    # ============================================================

    story.extend([
        H("01 / Ringkasan hasil"),
        table_pairs([
            (
                "Kandidat varian mentah",
                raw["total"] if raw is not None
                else getattr(run, "raw_variant_count", None),
            ),
            (
                "Varian lolos filter",
                getattr(run, "passed_variant_count", None),
            ),
            (
                "Varian tidak lolos filter",
                getattr(run, "filtered_variant_count", None),
            ),
            (
                "Varian teranotasi",
                getattr(run, "annotated_variant_count", None),
            ),
            (
                "Status SnpEff",
                _enum(getattr(run, "annotation_status", None)),
            ),
        ]),
        Spacer(1, 6 * mm),
        Bars(
            [
                (
                    "PASS",
                    getattr(run, "passed_variant_count", None),
                ),
                (
                    "Terfilter",
                    getattr(run, "filtered_variant_count", None),
                ),
            ],
            title="Hasil penyaringan varian",
        ),
    ])

    # ============================================================
    # 02 / QUALITY CONTROL
    # ============================================================

    story.extend([
        H("02 / Quality Control - fastp"),
        table_pairs([
            ("Reads sebelum", getattr(run, "reads_before", None)),
            ("Reads sesudah", getattr(run, "reads_after", None)),
            (
                "Reads dipertahankan",
                _num(getattr(run, "passed_reads_pct", None), 2, "%"),
            ),
            (
                "Q20 sebelum",
                _num(getattr(run, "q20_before", None), 2, "%"),
            ),
            (
                "Q20 sesudah",
                _num(getattr(run, "q20_rate", None), 2, "%"),
            ),
            (
                "Q30 sebelum",
                _num(getattr(run, "q30_before", None), 2, "%"),
            ),
            (
                "Q30 sesudah",
                _num(getattr(run, "q30_rate", None), 2, "%"),
            ),
            (
                "Reads dengan adapter terpotong",
                _num(
                    getattr(run, "adapter_trimmed_pct", None),
                    2,
                    "%",
                ),
            ),
        ]),
    ])

    qrows = [
        ("Q20 sebelum", getattr(run, "q20_before", None)),
        ("Q20 sesudah", getattr(run, "q20_rate", None)),
        ("Q30 sebelum", getattr(run, "q30_before", None)),
        ("Q30 sesudah", getattr(run, "q30_rate", None)),
    ]

    if any(value is not None for _, value in qrows):
        story.extend([
            Spacer(1, 4 * mm),
            Bars(
                qrows,
                title="Proporsi basa Q20 / Q30",
                unit="%",
            ),
        ])

    # ============================================================
    # 03 / ALIGNMENT
    # ============================================================

    story.extend([
        H("03 / Alignment dan cakupan genom"),
        table_pairs([
            (
                "Mapping rate",
                _num(getattr(run, "mapping_rate", None), 2, "%"),
            ),
            (
                "Unmapped alignment records",
                getattr(run, "unmapped_reads", None),
            ),
            (
                "Mean depth",
                _num(getattr(run, "mean_depth", None), 2, "x"),
            ),
            (
                "Coverage >=1x",
                _num(
                    coverage.get("genome_coverage_pct"),
                    2,
                    "%",
                ),
            ),
            (
                "Coverage >=30x",
                _num(
                    coverage.get("genome_coverage_30x_pct"),
                    2,
                    "%",
                ),
            ),
            (
                "Filter base quality (depth)",
                coverage.get("min_base_quality"),
            ),
            (
                "Filter mapping quality (depth)",
                coverage.get("min_mapping_quality"),
            ),
        ]),
        _paragraph(
            "Mapping rate, rata-rata depth, dan cakupan 1x/30x "
            "adalah ukuran berbeda. Mean depth tidak menjamin "
            "bahwa seluruh posisi genom tercakup.",
            styles["VSmall"],
        ),
    ])

    cover_rows = [
        (
            "Coverage >=1x",
            coverage.get("genome_coverage_pct"),
        ),
        (
            "Coverage >=30x",
            coverage.get("genome_coverage_30x_pct"),
        ),
    ]

    if any(value is not None for _, value in cover_rows):
        story.extend([
            Spacer(1, 4 * mm),
            Bars(
                cover_rows,
                title="Cakupan genom referensi",
                unit="%",
            ),
        ])

    # ============================================================
    # 04 / VARIANT CALLING
    # ============================================================

    story.append(
        H("04 / Variant calling dan komposisi perubahan")
    )

    if raw is not None:
        if raw["tv"]:
            ratio = f'{raw["ts"] / raw["tv"]:.3f}'
        else:
            ratio = "Tidak terdefinisi (Tv=0)"

        story.append(table_pairs([
            ("Raw SNP (bialelik A/C/G/T)", raw["snp"]),
            ("Raw INDEL", raw["indel"]),
            ("Transitions (Ts)", raw["ts"]),
            ("Transversions (Tv)", raw["tv"]),
            ("Rasio Ts/Tv raw VCF", ratio),
        ]))

        story.extend([
            Spacer(1, 4 * mm),
            Bars(
                [
                    ("SNP", raw["snp"]),
                    ("INDEL", raw["indel"]),
                ],
                title="SNP vs INDEL pada raw VCF",
            ),
        ])

        if raw["substitutions"]:
            story.append(Bars(
                sorted(raw["substitutions"].items()),
                title="Spektrum substitusi nukleotida raw VCF",
            ))

    else:
        story.append(P(
            "Raw VCF tidak tersedia pada arsip run ini; "
            "statistik rinci tidak dapat dihitung ulang."
        ))

        story.append(table_pairs([
            (
                "Raw SNP (tersimpan)",
                getattr(run, "raw_snp_count", None),
            ),
            (
                "Raw INDEL (tersimpan)",
                getattr(run, "raw_indel_count", None),
            ),
            (
                "Ts/Tv (tersimpan, sumber historis belum terverifikasi)",
                getattr(run, "tstv_ratio", None),
            ),
        ]))

    # ============================================================
    # 05 / ANOTASI SNPEFF
    # ============================================================

    story.append(
        H("05 / Anotasi SnpEff dari varian PASS")
    )

    annotation_status = str(
        _enum(getattr(run, "annotation_status", None)) or ""
    ).upper()

    if annotation_status == "SKIPPED":
        story.append(P(
            "Anotasi SnpEff tidak dijalankan (SKIPPED) "
            "karena tidak terdapat varian PASS setelah "
            "quality filtering."
        ))

    elif impact_counts:
        story.append(Bars(
            [
                (key, impact_counts[key])
                for key in ("HIGH", "MODERATE", "LOW", "MODIFIER")
                if key in impact_counts
            ],
            title="Distribusi kategori IMPACT SnpEff",
        ))
    else:
        story.append(P(
            "Kategori IMPACT tidak tersedia pada "
            "hasil anotasi yang tersimpan."
        ))

    if effect_counts:
        story.append(Bars(
            effect_counts.most_common(8),
            title="Efek SnpEff paling sering "
                  "(satu efek utama per varian)",
        ))

    if variants:
        story.append(GenomePlot([
            getattr(var, "position", None)
            for var in variants
        ]))

    story.append(_paragraph(
        "Kategori IMPACT merupakan konsekuensi anotasi "
        "sekuens, bukan prediksi fenotipe, keparahan klinis, "
        "transmisibilitas, atau immune escape.",
        styles["VSmall"],
    ))

    # ============================================================
    # 06 / PARAMETER DAN REPRODUKSIBILITAS
    # ============================================================

    story.extend([
        H("06 / Parameter analisis dan reproduksibilitas"),
        table_pairs([
            (
                "Execution mode",
                _enum(getattr(run, "execution_mode", None)),
            ),
            ("Min DP", getattr(run, "min_dp", None)),
            (
                "Min MQ (mpileup)",
                getattr(run, "min_mq", None),
            ),
            (
                "Min base quality (mpileup)",
                getattr(run, "min_base_quality", None),
            ),
            (
                "Max depth (mpileup)",
                getattr(run, "max_depth", None),
            ),
            (
                "Min QUAL (filter)",
                getattr(run, "min_qual", None),
            ),
            (
                "Min AF (filter)",
                getattr(run, "min_af", None),
            ),
        ]),
    ])

    try:
        versions = json.loads(
            getattr(run, "tool_versions_json", None) or "{}"
        )
    except (ValueError, TypeError):
        versions = {}

    if isinstance(versions, dict) and versions:
        story.extend([
            H("Versi perangkat lunak (rekaman run)"),
            table_pairs([
                (key, _s(value))
                for key, value in versions.items()
            ]),
        ])
    else:
        story.append(P(
            "Versi tool tidak direkam pada run ini."
        ))

    # ============================================================
    # 07 / INTERPRETASI DESKRIPTIF
    # ============================================================

    # Hanya SATU blok interpretasi, aman terhadap None.
    if isinstance(station_interpretations, dict):
        story.append(
            H("07 / Interpretasi deskriptif per stasiun")
        )

        found_interpretation = False

        for station_number in range(1, 5):
            entry = (
                station_interpretations.get(
                    f"station_{station_number}"
                )
                or {}
            )

            if not isinstance(entry, dict):
                continue

            interpretation = entry.get("interpretation")

            if not interpretation:
                continue

            found_interpretation = True

            story.append(_paragraph(
                f"Stasiun {station_number}: {interpretation}",
                styles["VText"],
            ))

            notes = entry.get("notes") or []

            if isinstance(notes, (list, tuple)):
                for note in notes[:5]:
                    if note:
                        story.append(_paragraph(
                            f"Catatan: {note}",
                            styles["VSmall"],
                        ))

        if not found_interpretation:
            story.append(P(
                "Interpretasi deskriptif per stasiun "
                "belum tersedia pada data laporan ini."
            ))

    # ============================================================
    # 08 / AUDIT QUALITY FILTERING
    # ============================================================

    story.append(
        H("08 / Audit Quality Filtering")
    )

    if filter_audit is None:
        story.append(P(
            "Data audit filtering tidak tersedia pada "
            "laporan ini. Ketiadaan data audit bukan "
            "berarti semua varian lolos."
        ))

    else:
        audit_rows = list(filter_audit)

        passed_rows = [
            item
            for item in audit_rows
            if str(item.filter_status).upper() == "PASS"
        ]

        filtered_rows = [
            item
            for item in audit_rows
            if str(item.filter_status).upper() == "FILTERED"
        ]

        story.append(table_pairs([
            (
                "Total kandidat dalam audit",
                len(audit_rows),
            ),
            ("Varian PASS", len(passed_rows)),
            ("Varian FILTERED", len(filtered_rows)),
        ]))

        if not audit_rows:
            story.append(P(
                "Tidak ada record audit filtering yang "
                "tersimpan untuk run ini."
            ))

        elif not filtered_rows:
            story.append(P(
                "Tidak terdapat kandidat varian berstatus "
                "FILTERED pada data audit yang tersedia."
            ))

        else:
            story.append(Spacer(1, 4 * mm))

            story.append(P(
                "Tabel berikut memuat kandidat varian "
                "yang tidak memenuhi parameter quality "
                "filtering. Alasan penolakan berasal dari "
                "database VarEscape."
            ))

            headers = [
                "POSISI",
                "REF > ALT",
                "DP",
                "QUAL",
                "AF",
                "STATUS",
                "ALASAN FILTERING",
            ]

            audit_table_data = [[
                _paragraph(
                    header,
                    styles["VAuditHeader"],
                )
                for header in headers
            ]]

            def audit_num(value, digits=2):
                if value is None:
                    return "-"

                try:
                    return (
                        f"{float(value):,.{digits}f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                except (ValueError, TypeError):
                    return str(value)

            for item in filtered_rows:
                values = [
                    audit_num(item.position, 0),
                    (
                        f"{_s(item.ref_allele)} > "
                        f"{_s(item.alt_allele)}"
                    ),
                    audit_num(item.dp, 0),
                    audit_num(item.qual, 3),
                    audit_num(item.af, 4),
                    _s(item.filter_status),
                    _s(item.filter_reason),
                ]

                audit_table_data.append([
                    _paragraph(
                        value,
                        styles["VAuditCell"],
                    )
                    for value in values
                ])

            audit_table = Table(
                audit_table_data,
                colWidths=[
                    19 * mm,
                    27 * mm,
                    14 * mm,
                    19 * mm,
                    15 * mm,
                    19 * mm,
                    55 * mm,
                ],
                repeatRows=1,
                hAlign="LEFT",
            )

            audit_table.setStyle(TableStyle([
                (
                    "BACKGROUND",
                    (0, 0), (-1, 0),
                    DARK,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1), (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F4F8F8"),
                    ],
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "LINEBELOW",
                    (0, 0), (-1, -1),
                    0.25,
                    colors.HexColor("#DDE7EA"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))

            story.append(audit_table)
            story.append(Spacer(1, 4 * mm))

            story.append(_paragraph(
                "Varian FILTERED tidak diteruskan ke "
                "anotasi SnpEff. Status FILTERED berarti "
                "kandidat tidak memenuhi ambang filtering "
                "pada run ini, bukan bukti bahwa perubahan "
                "biologis tersebut tidak ada.",
                styles["VSmall"],
            ))

    # ============================================================
    # BATASAN INTERPRETASI
    # ============================================================

    story.extend([
        H("Batasan interpretasi"),
        P(
            "Laporan ini merupakan ringkasan komputasional "
            "dari data tersimpan. Nilai yang tidak tersedia "
            "tidak dianggap nol. Varian PASS bukan bukti "
            "signifikansi klinis; anotasi efek SnpEff tidak "
            "mengevaluasi epitope atau immune escape."
        ),
        _paragraph(
            "PDF dihasilkan dari database dan artefak "
            "run yang tersimpan tanpa menjalankan "
            "ulang pipeline.",
            styles["VSmall"],
        ),
    ])

    doc.build(story)

    return buffer.getvalue()
