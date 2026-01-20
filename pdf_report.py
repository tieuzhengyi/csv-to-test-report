from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from validator import validate_csv
from engine import evaluate
from charts import generate_histogram, generate_scatter


def _verdict_color(verdict: str):
    return colors.green if verdict == "PASS" else colors.red


def build_pdf_report(
    csv_path: str,
    out_pdf_path: str,
    report_title: str = "Test Report",
    company_name: str | None = None,
):
    out_pdf = Path(out_pdf_path)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    # 1) Load + evaluate
    df = validate_csv(csv_path)
    results_df, summary = evaluate(df)

    # 2) Charts (saved as images)
    output_dir = out_pdf.parent
    hist_path = str(output_dir / "histogram.png")
    scatter_path = str(output_dir / "scatter.png")
    generate_histogram(results_df, hist_path)
    generate_scatter(results_df, scatter_path)

    # 3) PDF setup
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=report_title,
    )

    styles = getSampleStyleSheet()
    story = []

    # ---------- Page 1: Overview ----------
    title = report_title
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))

    if company_name:
        story.append(Spacer(1, 4))
        story.append(Paragraph(company_name, styles["Heading3"]))

    story.append(Spacer(1, 8))

    # Overview table
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overview_data = [
        ["Generated", now_str],
        ["Total Measurements", str(summary["total"])],
        ["Pass Count", str(summary["pass_count"])],
        ["Fail Count", str(summary["fail_count"])],
        ["Pass Rate", f'{summary["pass_rate"]:.2f}%'],
        ["Overall Verdict", summary["overall_verdict"]],
    ]

    overview_table = Table(
        overview_data,
        colWidths=[55 * mm, 110 * mm],
        hAlign="LEFT",
    )

    verdict = summary["overall_verdict"]
    overview_style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
        ]
    )

    # Highlight verdict row
    verdict_row_index = len(overview_data) - 1
    overview_style.add("TEXTCOLOR", (1, verdict_row_index), (1, verdict_row_index), _verdict_color(verdict))
    overview_style.add("FONTNAME", (1, verdict_row_index), (1, verdict_row_index), "Helvetica-Bold")

    overview_table.setStyle(overview_style)
    story.append(overview_table)

    story.append(Spacer(1, 14))
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "This report was generated automatically from the uploaded CSV/Excel dataset. "
            "Pass/Fail is evaluated per measurement using the provided limits.",
            styles["BodyText"],
        )
    )

    story.append(PageBreak())

    # ---------- Page 2: Charts ----------
    story.append(Paragraph("Charts", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Histogram
    if Path(hist_path).exists():
        story.append(Paragraph("Measurement Distribution", styles["Heading3"]))
        story.append(Spacer(1, 6))
        story.append(Image(hist_path, width=170 * mm, height=85 * mm))
        story.append(Spacer(1, 10))

    # Scatter
    if Path(scatter_path).exists():
        story.append(Paragraph("Value vs Sample ID", styles["Heading3"]))
        story.append(Spacer(1, 6))
        story.append(Image(scatter_path, width=170 * mm, height=85 * mm))

    story.append(PageBreak())

    # ---------- Page 3: Detailed Results ----------
    story.append(Paragraph("Detailed Results", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Build detailed table (limit row count for v1; later we’ll paginate)
    # Keep it sane for now: first 200 rows
    max_rows = 200
    view_df = results_df.head(max_rows).copy()

    # Ensure unit exists
    if "unit" not in view_df.columns:
        view_df["unit"] = ""

    table_data = [["Sample", "Test", "Value", "Lower", "Upper", "Unit", "Status"]]
    for _, r in view_df.iterrows():
        table_data.append(
            [
                str(r["sample_id"]),
                str(r["test_name"]),
                f'{float(r["value"]):.6g}',
                f'{float(r["lower_limit"]):.6g}',
                f'{float(r["upper_limit"]):.6g}',
                str(r["unit"]),
                str(r["status"]),
            ]
        )

    detail_table = Table(
        table_data,
        colWidths=[26 * mm, 35 * mm, 24 * mm, 24 * mm, 24 * mm, 18 * mm, 20 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )

    detail_style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1,-1), "MIDDLE"),
        ]
    )

    # Highlight FAIL rows
    for i in range(1, len(table_data)):
        status = table_data[i][-1]
        if status == "FAIL":
            detail_style.add("TEXTCOLOR", (-1, i), (-1, i), colors.red)
            detail_style.add("FONTNAME", (-1, i), (-1, i), "Helvetica-Bold")

    detail_table.setStyle(detail_style)
    story.append(detail_table)

    story.append(Spacer(1, 10))
    if len(results_df) > max_rows:
        story.append(
            Paragraph(
                f"Note: Showing first {max_rows} rows only. (We’ll add paging/export options later.)",
                styles["Italic"],
            )
        )

    # Footer note
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"Generated by Report Engine • {now_str}",
            styles["Normal"],
        )
    )

    doc.build(story)


if __name__ == "__main__":
    build_pdf_report(
        csv_path="sample.csv",
        out_pdf_path="output/report.pdf",
        report_title="Automated Test Report",
        company_name="(Optional) Your Company Name",
    )
    print("✅ PDF generated: output/report.pdf")
