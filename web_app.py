from datetime import datetime
from pathlib import Path
import uuid
import time

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse

from pdf_report import build_pdf_report

APP_DIR = Path(__file__).parent
RUNS_DIR = APP_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CSV to Test Report")


# -------------------------
# Helpers
# -------------------------

def cleanup_runs(older_than_hours: int = 6):
    cutoff = time.time() - older_than_hours * 3600
    for p in RUNS_DIR.iterdir():
        try:
            if p.is_dir() and p.stat().st_mtime < cutoff:
                for f in p.rglob("*"):
                    if f.is_file():
                        f.unlink()
                p.rmdir()
        except Exception:
            pass


def friendly_error(e: Exception) -> str:
    s = str(e)
    if "Missing required columns" in s:
        return s + " Please use the template CSV."
    if "must be numeric" in s:
        return s + " Ensure value and limits are numeric."
    return s


def html_page(message: str = "", success: bool = False) -> str:
    color = "#0a7a2f" if success else "#b00020"
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>CSV → Test Report PDF</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; }}
    h1 {{ margin-bottom: 6px; }}
    .row {{ display:flex; gap:20px; flex-wrap:wrap; }}
    .card {{ flex:1; min-width:280px; border:1px solid #eee; border-radius:14px; padding:18px; box-shadow:0 2px 10px rgba(0,0,0,0.04); }}
    label {{ display:block; margin-top:12px; font-weight:600; }}
    input[type="text"] {{ width:100%; padding:10px; border-radius:10px; border:1px solid #ddd; }}
    input[type="file"] {{ margin-top:6px; }}
    button {{ margin-top:16px; padding:10px 14px; border-radius:12px; border:0; cursor:pointer; }}
    ul {{ margin:8px 0 0 18px; }}
    .hint {{ color:#666; font-size:14px; line-height:1.5; }}
    .msg {{ margin-top:12px; color:{color}; }}
    code {{ background:#f5f5f5; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>

<h1>CSV → Test Report (PDF)</h1>
<p class="hint">
Upload raw test data and instantly get a professional PDF report with summary, charts, and pass/fail results.
</p>

<div class="row">

  <div class="card">
    <h3>1) Upload CSV</h3>
    <form action="/generate" method="post" enctype="multipart/form-data" onsubmit="showLoading()">
      <label>CSV file</label>
      <input name="file" type="file" accept=".csv" required />

      <label>Report title (optional)</label>
      <input name="report_title" type="text" placeholder="Automated Test Report"/>

      <label>Company name (optional)</label>
      <input name="company_name" type="text" placeholder="Your Company"/>

      <button type="submit">Generate PDF</button>
    </form>

    <div id="loading" class="hint" style="display:none;margin-top:10px;">
      Generating report… please wait.
    </div>

    <div class="msg">{message}</div>
  </div>

  <div class="card">
    <h3>2) CSV format</h3>
    <div class="hint">
      Required columns:
      <ul>
        <li><code>sample_id</code></li>
        <li><code>test_name</code></li>
        <li><code>value</code></li>
        <li><code>lower_limit</code></li>
        <li><code>upper_limit</code></li>
      </ul>
      Optional: <code>unit</code>
      <p style="margin-top:10px;">
        <a href="/template">Download template CSV</a>
      </p>
    </div>
  </div>

</div>

<script>
function showLoading() {{
  document.getElementById("loading").style.display = "block";
}}
</script>

</body>
</html>
""".strip()


# -------------------------
# Routes
# -------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return html_page()


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
    cleanup_runs()

    if not file.filename.lower().endswith(".csv"):
        return HTMLResponse(html_page("Please upload a .csv file."), status_code=400)

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return HTMLResponse(html_page("File too large (max 5MB)."), status_code=400)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_path = run_dir / "input.csv"
    pdf_path = run_dir / "report.pdf"
    csv_path.write_bytes(content)

    try:
        build_pdf_report(
            csv_path=str(csv_path),
            out_pdf_path=str(pdf_path),
            report_title=report_title.strip() or "Automated Test Report",
            company_name=company_name.strip() or None,
        )
    except Exception as e:
        return HTMLResponse(html_page("Error: " + friendly_error(e)), status_code=400)

    return HTMLResponse(
        f"""
        <html><body style="font-family:Arial;max-width:720px;margin:40px auto;padding:0 16px;">
        <h2>✅ Report generated</h2>
        <p><a href="/download/{run_id}">Download PDF</a></p>
        <p><a href="/">Generate another report</a></p>
        </body></html>
        """,
        status_code=200,
    )


@app.get("/download/{run_id}")
def download(run_id: str):
    pdf_path = RUNS_DIR / run_id / "report.pdf"
    if not pdf_path.exists():
        return HTMLResponse(html_page("Report not found or expired."))
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="test-report.pdf",
    )
