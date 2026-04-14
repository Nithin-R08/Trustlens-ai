from __future__ import annotations

import json
from io import BytesIO
from typing import Any

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception:  # pragma: no cover - optional dependency
    canvas = None
    letter = (612, 792)


def _wrap_text(text: str, line_width: int = 92) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        projected = current_len + len(word) + (1 if current else 0)
        if projected > line_width:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len = projected

    if current:
        lines.append(" ".join(current))
    return lines


def generate_pdf_report(result: dict[str, Any]) -> bytes:
    if canvas is None:
        raise RuntimeError("PDF generation requires the `reportlab` package.")

    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=letter)
    width, height = letter
    y = height - 48

    def draw_line(text: str, *, font: str = "Helvetica", size: int = 10, gap: int = 14) -> None:
        nonlocal y
        if y <= 48:
            pdf.showPage()
            y = height - 48
        pdf.setFont(font, size)
        pdf.drawString(40, y, text)
        y -= gap

    draw_line("TrustLens AI - Dataset Bias Detection Report", font="Helvetica-Bold", size=16, gap=20)
    draw_line(f"Analysis ID: {result.get('id', '-')}", font="Helvetica", size=10)
    draw_line(f"Dataset: {result.get('dataset_name', '-')}", font="Helvetica", size=10)
    draw_line(f"Trust Score: {result.get('trust_score', '-')}", font="Helvetica-Bold", size=11, gap=16)
    draw_line(f"Bias Risk: {result.get('bias_risk', '-')}", font="Helvetica-Bold", size=11, gap=18)

    draw_line("Sensitive Attributes", font="Helvetica-Bold", size=12, gap=16)
    attrs = result.get("sensitive_attributes", [])
    draw_line(", ".join(attrs) if attrs else "None detected")
    y -= 8

    draw_line("Metrics", font="Helvetica-Bold", size=12, gap=16)
    metrics = result.get("metrics", {})
    metric_lines = [
        f"Demographic Parity Difference: {metrics.get('demographic_parity_difference')}",
        f"Disparate Impact Ratio: {metrics.get('disparate_impact_ratio')}",
        f"Statistical Parity: {metrics.get('statistical_parity')}",
        f"Representation Imbalance Score: {metrics.get('representation_imbalance_score')}",
    ]
    for line in metric_lines:
        draw_line(line)
    y -= 8

    draw_line("Insights", font="Helvetica-Bold", size=12, gap=16)
    for line in _wrap_text(str(result.get("insights", "")), line_width=100):
        draw_line(line)
    y -= 8

    draw_line("Recommendations", font="Helvetica-Bold", size=12, gap=16)
    recommendations = result.get("recommendations", [])
    for recommendation in recommendations:
        for index, line in enumerate(_wrap_text(str(recommendation), line_width=95)):
            prefix = "- " if index == 0 else "  "
            draw_line(prefix + line)

    y -= 8
    draw_line("Raw JSON Summary", font="Helvetica-Bold", size=12, gap=16)
    raw_json = json.dumps(result.get("details", {}), indent=2)
    for line in raw_json.splitlines()[:120]:
        draw_line(line[:120], font="Courier", size=8, gap=10)

    pdf.save()
    stream.seek(0)
    return stream.read()

