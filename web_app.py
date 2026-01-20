from datetime import datetime
from pathlib import Path
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse

from pdf_report import build_pdf_report

APP_DIR = Path(__file__).parent
RUNS_DIR = APP_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CSV to Test Report")


def _html_page(message: str = "") -> str:
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>CSV → Test Report PDF</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; }}
    .card {{ border: 1px solid #eee; border-radius: 14px; padding: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.04); }}
    label {{ display:block; margin-top: 12px; font-weight: 600; }}
    input[type="text"] {{ width: 100%; padding: 10px; border-radius: 10px; border:1px solid #ddd; }}
    input[type="file"] {{ margin-top: 8px; }}
    button {{ margin-top: 16px; padding: 10px 14px; border-radius: 12px; border: 0; cursor: pointer; }}
    .msg {{ margin-top: 12px; color: #b00020; }}
    .hint {{ color:#666; font-size: 14px; margin-top: 10px; }}
  </style>
</head>
<body>
  <h1>CSV → Test Report (PDF)</h1>
  <p class="hint">Upload your CSV in the required format and download a professional PDF report.</p>

  <div class="card">
    <form action="/generate" method="post" enctype="multipart/form-data">
      <label>CSV file</label>
      <input name="file" type="file" accept=".csv" required />

      <label>Report title (optional)</label>
      <input name="report_title" type="text" placeholder="Automated Test Report"/>

      <label>Company name (optional)</label>
      <input name="company_name" type="text" placeholder="Your Company"/>

      <button type="submit">Generate PDF</button>
    </form>
    <div class="msg">{message}</div>
  </div>

  <p class="hint">
    Need a template CSV? <a href="/template">Download template</a>
  </p>
</body>
</html>
""".strip()


@app.get("/", response_class=HTMLResponse)
def home():
    return _html_page("")


@app.get("/template")
def template_csv():
    template_path = APP_DIR / "template.csv"
    if not template_path.exists():
        template_path.write_text(
            "sample_id,test_name,value,lower_limit,upper_limit,unit\n"
            "DUT_001,Output Power,-12.4,-15,-10,dBm\n"
        )
    return FileResponse(
        path=str(template_path),
        media_type="text/csv",
        filename="template.csv",
    )


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    report_title: str = Form("Automated Test Report"),
    company_name: str = Form(""),
):
    # Basic file checks
    if not file.filename.lower().endswith(".csv"):
        return HTMLResponse(_html_page("Please upload a .csv file."), status_code=400)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_path = run_dir / "input.csv"
    pdf_path = run_dir / "report.pdf"

    # Save upload
    content = await file.read()
    csv_path.write_bytes(content)

    try:
        build_pdf_report(
            csv_path=str(csv_path),
            out_pdf_path=str(pdf_path),
            report_title=report_title.strip() or "Automated Test Report",
            company_name=company_name.strip() or None,
        )
    except Exception as e:
        # Show friendly error
        return HTMLResponse(_html_page(f"Error: {e}"), status_code=400)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="report.pdf",
    )
