#!/usr/bin/env python3
"""CI Metrics Dashboard Generator.

Queries BigQuery for test metrics and generates a static HTML dashboard
that integrates into the MkDocs Operations Portal via GitLab Pages.

Usage (CI):
    python scripts/generate-dashboard.py

Usage (local):
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json python scripts/generate-dashboard.py

Output: docs/ci-dashboard.html

Ref: Issue #40, ADR INF-001 Phase 4
"""

import json
import os
import sys
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────
GCP_PROJECT = os.environ.get("CI_METRICS_GCP_PROJECT", "myk8sproject-207017")
BQ_DATASET = os.environ.get("CI_METRICS_BQ_DATASET", "ci_metrics")
OUTPUT_PATH = os.environ.get("DASHBOARD_OUTPUT", "docs/ci-dashboard.html")


def query_bigquery():
    """Fetch all dashboard data from BigQuery."""
    try:
        from google.cloud import bigquery
    except ImportError:
        print("❌ google-cloud-bigquery not installed")
        sys.exit(1)

    sa_key_b64 = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if sa_key_b64:
        import base64, tempfile
        from google.oauth2 import service_account
        key_json = base64.b64decode(sa_key_b64).decode()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(key_json)
            key_path = f.name
        credentials = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        client = bigquery.Client(project=GCP_PROJECT, credentials=credentials)
        os.unlink(key_path)
    else:
        client = bigquery.Client(project=GCP_PROJECT)

    dataset = f"{GCP_PROJECT}.{BQ_DATASET}"

    # 1. Overall summary
    summary = {}
    for r in client.query(f"""
        SELECT
            COUNT(DISTINCT pipeline_id) as pipelines,
            COUNT(*) as runs,
            SUM(tests) as total_tests,
            SUM(passed) as total_passed,
            SUM(failed) as total_failed,
            SUM(skipped) as total_skipped,
            ROUND(SAFE_DIVIDE(SUM(passed), SUM(tests)) * 100, 1) as pass_rate,
            ROUND(AVG(duration_s), 2) as avg_duration,
            MAX(ingested_at) as last_ingested
        FROM `{dataset}.test_runs`
        WHERE pipeline_id > 0
    """).result():
        summary = {
            "pipelines": r.pipelines or 0,
            "runs": r.runs or 0,
            "total_tests": r.total_tests or 0,
            "total_passed": r.total_passed or 0,
            "total_failed": r.total_failed or 0,
            "total_skipped": r.total_skipped or 0,
            "pass_rate": float(r.pass_rate or 0),
            "avg_duration": float(r.avg_duration or 0),
            "last_ingested": r.last_ingested.isoformat() if r.last_ingested else None,
        }

    # 2. Pipeline history (last 50)
    pipeline_history = []
    for r in client.query(f"""
        SELECT
            pipeline_id,
            ref,
            commit_sha,
            STRING_AGG(DISTINCT job_name, ', ') as jobs,
            SUM(tests) as tests,
            SUM(passed) as passed,
            SUM(failed) as failed,
            ROUND(SAFE_DIVIDE(SUM(passed), SUM(tests)) * 100, 1) as pass_rate,
            ROUND(SUM(duration_s), 1) as total_duration,
            MAX(ingested_at) as ingested_at
        FROM `{dataset}.test_runs`
        WHERE pipeline_id > 0
        GROUP BY pipeline_id, ref, commit_sha
        ORDER BY ingested_at DESC
        LIMIT 50
    """).result():
        pipeline_history.append({
            "pipeline_id": r.pipeline_id,
            "ref": r.ref,
            "commit_sha": r.commit_sha[:8] if r.commit_sha else "",
            "jobs": r.jobs,
            "tests": r.tests,
            "passed": r.passed,
            "failed": r.failed,
            "pass_rate": float(r.pass_rate or 0),
            "duration": float(r.total_duration or 0),
            "timestamp": r.ingested_at.isoformat() if r.ingested_at else "",
        })

    # 3. Daily trend (last 30 days)
    daily_trend = []
    for r in client.query(f"""
        SELECT
            DATE(ingested_at) as day,
            COUNT(DISTINCT pipeline_id) as pipelines,
            SUM(tests) as tests,
            SUM(passed) as passed,
            SUM(failed) as failed,
            ROUND(SAFE_DIVIDE(SUM(passed), SUM(tests)) * 100, 1) as pass_rate,
            ROUND(AVG(duration_s), 2) as avg_duration
        FROM `{dataset}.test_runs`
        WHERE pipeline_id > 0
          AND ingested_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        GROUP BY day
        ORDER BY day ASC
    """).result():
        daily_trend.append({
            "day": r.day.isoformat(),
            "pipelines": r.pipelines,
            "tests": r.tests,
            "passed": r.passed,
            "failed": r.failed,
            "pass_rate": float(r.pass_rate or 0),
            "avg_duration": float(r.avg_duration or 0),
        })

    # 4. Recent failures (last 20)
    recent_failures = []
    for r in client.query(f"""
        SELECT
            pipeline_id,
            job_name,
            suite_name,
            test_name,
            classname,
            message,
            duration_s,
            ingested_at
        FROM `{dataset}.test_cases`
        WHERE status IN ('failed', 'error')
          AND pipeline_id > 0
        ORDER BY ingested_at DESC
        LIMIT 20
    """).result():
        recent_failures.append({
            "pipeline_id": r.pipeline_id,
            "job_name": r.job_name,
            "suite": r.suite_name,
            "test": r.test_name,
            "classname": r.classname,
            "message": (r.message or "")[:200],
            "duration": float(r.duration_s or 0),
            "timestamp": r.ingested_at.isoformat() if r.ingested_at else "",
        })

    # 5. Top flaky tests (failed more than once)
    flaky_tests = []
    for r in client.query(f"""
        SELECT
            test_name,
            classname,
            COUNT(*) as failure_count,
            COUNT(DISTINCT pipeline_id) as pipelines_affected,
            MAX(ingested_at) as last_failure
        FROM `{dataset}.test_cases`
        WHERE status IN ('failed', 'error')
          AND pipeline_id > 0
        GROUP BY test_name, classname
        HAVING COUNT(*) > 1
        ORDER BY failure_count DESC
        LIMIT 10
    """).result():
        flaky_tests.append({
            "test": r.test_name,
            "classname": r.classname,
            "failures": r.failure_count,
            "pipelines": r.pipelines_affected,
            "last": r.last_failure.isoformat() if r.last_failure else "",
        })

    # 6. Job breakdown
    job_stats = []
    for r in client.query(f"""
        SELECT
            job_name,
            COUNT(DISTINCT pipeline_id) as runs,
            SUM(tests) as tests,
            ROUND(SAFE_DIVIDE(SUM(passed), SUM(tests)) * 100, 1) as pass_rate,
            ROUND(AVG(duration_s), 2) as avg_duration
        FROM `{dataset}.test_runs`
        WHERE pipeline_id > 0
        GROUP BY job_name
        ORDER BY runs DESC
    """).result():
        job_stats.append({
            "job": r.job_name,
            "runs": r.runs,
            "tests": r.tests,
            "pass_rate": float(r.pass_rate or 0),
            "avg_duration": float(r.avg_duration or 0),
        })

    return {
        "summary": summary,
        "pipeline_history": pipeline_history,
        "daily_trend": daily_trend,
        "recent_failures": recent_failures,
        "flaky_tests": flaky_tests,
        "job_stats": job_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_html(data: dict) -> str:
    """Generate the dashboard HTML with embedded data and Chart.js."""
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CI Metrics Dashboard — Blauweiss Ops</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #1a1a2e; --bg2: #16213e; --bg3: #0f3460;
    --fg: #e4e4e4; --fg2: #a0a0b0; --accent: #e94560;
    --green: #4ade80; --red: #f87171; --yellow: #fbbf24;
    --blue: #60a5fa; --purple: #a78bfa;
    --radius: 12px; --shadow: 0 4px 20px rgba(0,0,0,0.3);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--fg);
    padding: 24px; max-width: 1400px; margin: 0 auto;
  }}

  /* Header */
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 28px; padding-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }}
  .header h1 {{ font-size: 1.6rem; font-weight: 700; }}
  .header h1 span {{ color: var(--accent); }}
  .header .meta {{ color: var(--fg2); font-size: 0.82rem; }}

  /* KPI Cards */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 28px;
  }}
  .kpi {{
    background: var(--bg2); border-radius: var(--radius);
    padding: 20px; box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,0.05);
  }}
  .kpi .label {{ font-size: 0.75rem; color: var(--fg2); text-transform: uppercase; letter-spacing: 0.05em; }}
  .kpi .value {{ font-size: 2rem; font-weight: 800; margin-top: 4px; }}
  .kpi .sub {{ font-size: 0.78rem; color: var(--fg2); margin-top: 2px; }}
  .kpi.green .value {{ color: var(--green); }}
  .kpi.red .value {{ color: var(--red); }}
  .kpi.blue .value {{ color: var(--blue); }}
  .kpi.purple .value {{ color: var(--purple); }}
  .kpi.yellow .value {{ color: var(--yellow); }}

  /* Charts */
  .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }}
  @media (max-width: 900px) {{ .charts {{ grid-template-columns: 1fr; }} }}
  .chart-card {{
    background: var(--bg2); border-radius: var(--radius);
    padding: 20px; box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,0.05);
  }}
  .chart-card h3 {{ font-size: 0.95rem; margin-bottom: 12px; color: var(--fg2); }}
  .chart-card canvas {{ max-height: 260px; }}

  /* Tables */
  .table-card {{
    background: var(--bg2); border-radius: var(--radius);
    padding: 20px; margin-bottom: 20px; box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,0.05);
    overflow-x: auto;
  }}
  .table-card h3 {{ font-size: 0.95rem; margin-bottom: 12px; color: var(--fg2); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th {{ text-align: left; padding: 8px 10px; color: var(--fg2); font-weight: 600;
       border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.75rem;
       text-transform: uppercase; letter-spacing: 0.04em; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .badge {{
    display: inline-block; padding: 2px 8px; border-radius: 6px;
    font-size: 0.72rem; font-weight: 600;
  }}
  .badge.pass {{ background: rgba(74,222,128,0.15); color: var(--green); }}
  .badge.fail {{ background: rgba(248,113,113,0.15); color: var(--red); }}
  .badge.warn {{ background: rgba(251,191,36,0.15); color: var(--yellow); }}
  .mono {{ font-family: 'SF Mono', Monaco, monospace; font-size: 0.78rem; }}
  .msg {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg2); }}

  /* Empty state */
  .empty {{ text-align: center; padding: 40px; color: var(--fg2); }}
  .empty .icon {{ font-size: 2.5rem; margin-bottom: 12px; }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 CI <span>Metrics</span> Dashboard</h1>
  <div class="meta">
    Generated: <span id="gen-time"></span><br>
    Data source: BigQuery <code>{GCP_PROJECT}.{BQ_DATASET}</code>
  </div>
</div>

<div id="app"></div>

<script>
const DATA = {json.dumps(data, default=str)};

const app = document.getElementById('app');
const s = DATA.summary;

// Format helpers
const fmt = (n) => n != null ? n.toLocaleString() : '—';
const fmtPct = (n) => n != null ? n.toFixed(1) + '%' : '—';
const fmtDur = (n) => n != null ? n.toFixed(1) + 's' : '—';
const fmtTime = (iso) => {{
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('de-AT', {{ day: '2-digit', month: '2-digit', year: '2-digit' }})
    + ' ' + d.toLocaleTimeString('de-AT', {{ hour: '2-digit', minute: '2-digit' }});
}};
const passClass = (rate) => rate >= 95 ? 'pass' : rate >= 80 ? 'warn' : 'fail';

document.getElementById('gen-time').textContent = fmtTime(DATA.generated_at);

// Empty state check
if (!s.pipelines) {{
  app.innerHTML = `<div class="empty"><div class="icon">📭</div>
    <h3>No test data yet</h3>
    <p>Run a pipeline with test jobs to see metrics here.</p></div>`;
}} else {{

  // ── KPI Cards ──
  app.innerHTML = `
  <div class="kpi-grid">
    <div class="kpi blue"><div class="label">Pipelines</div>
      <div class="value">${{fmt(s.pipelines)}}</div>
      <div class="sub">${{fmt(s.runs)}} test suite runs</div></div>
    <div class="kpi ${{s.pass_rate >= 95 ? 'green' : s.pass_rate >= 80 ? 'yellow' : 'red'}}">
      <div class="label">Pass Rate</div>
      <div class="value">${{fmtPct(s.pass_rate)}}</div>
      <div class="sub">${{fmt(s.total_passed)}} / ${{fmt(s.total_tests)}} tests</div></div>
    <div class="kpi red"><div class="label">Failures</div>
      <div class="value">${{fmt(s.total_failed)}}</div>
      <div class="sub">${{fmt(s.total_skipped)}} skipped</div></div>
    <div class="kpi purple"><div class="label">Avg Duration</div>
      <div class="value">${{fmtDur(s.avg_duration)}}</div>
      <div class="sub">per test suite</div></div>
    <div class="kpi yellow"><div class="label">Last Ingested</div>
      <div class="value" style="font-size:1.1rem">${{fmtTime(s.last_ingested)}}</div>
      <div class="sub">most recent data</div></div>
  </div>

  <div class="charts">
    <div class="chart-card"><h3>📈 Pass Rate Trend (30 days)</h3><canvas id="chartPassRate"></canvas></div>
    <div class="chart-card"><h3>⏱️ Duration Trend (30 days)</h3><canvas id="chartDuration"></canvas></div>
  </div>

  <div class="table-card"><h3>🏗️ Job Breakdown</h3>
    <table><thead><tr><th>Job</th><th>Runs</th><th>Tests</th><th>Pass Rate</th><th>Avg Duration</th></tr></thead>
    <tbody>${{DATA.job_stats.map(j => `<tr>
      <td class="mono">${{j.job}}</td><td>${{fmt(j.runs)}}</td><td>${{fmt(j.tests)}}</td>
      <td><span class="badge ${{passClass(j.pass_rate)}}">${{fmtPct(j.pass_rate)}}</span></td>
      <td>${{fmtDur(j.avg_duration)}}</td></tr>`).join('')}}</tbody></table>
  </div>

  <div class="table-card"><h3>🔴 Recent Failures</h3>
    ${{DATA.recent_failures.length ? `<table><thead><tr>
      <th>Pipeline</th><th>Job</th><th>Test</th><th>Message</th><th>When</th></tr></thead>
    <tbody>${{DATA.recent_failures.map(f => `<tr>
      <td class="mono">#${{f.pipeline_id}}</td>
      <td class="mono">${{f.job_name}}</td>
      <td class="mono">${{f.test}}</td>
      <td class="msg" title="${{f.message.replace(/"/g, '&quot;')}}">${{f.message || '—'}}</td>
      <td>${{fmtTime(f.timestamp)}}</td></tr>`).join('')}}</tbody></table>`
    : '<p style="color:var(--fg2);text-align:center;padding:20px">🎉 No failures!</p>'}}
  </div>

  ${{DATA.flaky_tests.length ? `<div class="table-card"><h3>🔄 Flaky Tests (failed in multiple pipelines)</h3>
    <table><thead><tr><th>Test</th><th>Class</th><th>Failures</th><th>Pipelines</th><th>Last Failure</th></tr></thead>
    <tbody>${{DATA.flaky_tests.map(f => `<tr>
      <td class="mono">${{f.test}}</td><td class="mono">${{f.classname}}</td>
      <td><span class="badge fail">${{f.failures}}</span></td>
      <td>${{f.pipelines}}</td><td>${{fmtTime(f.last)}}</td></tr>`).join('')}}</tbody></table>
  </div>` : ''}}

  <div class="table-card"><h3>📋 Pipeline History (last 50)</h3>
    <table><thead><tr><th>Pipeline</th><th>Branch</th><th>Commit</th><th>Jobs</th>
      <th>Tests</th><th>Pass Rate</th><th>Duration</th><th>When</th></tr></thead>
    <tbody>${{DATA.pipeline_history.map(p => `<tr>
      <td class="mono">#${{p.pipeline_id}}</td>
      <td class="mono">${{p.ref}}</td>
      <td class="mono">${{p.commit_sha}}</td>
      <td class="mono">${{p.jobs}}</td>
      <td>${{fmt(p.tests)}}</td>
      <td><span class="badge ${{passClass(p.pass_rate)}}">${{fmtPct(p.pass_rate)}}</span></td>
      <td>${{fmtDur(p.duration)}}</td>
      <td>${{fmtTime(p.timestamp)}}</td></tr>`).join('')}}</tbody></table>
  </div>`;

  // ── Charts ──
  const trend = DATA.daily_trend;
  if (trend.length > 0) {{
    const labels = trend.map(d => d.day.slice(5));  // MM-DD

    new Chart(document.getElementById('chartPassRate'), {{
      type: 'line',
      data: {{
        labels,
        datasets: [{{
          label: 'Pass Rate %',
          data: trend.map(d => d.pass_rate),
          borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)',
          fill: true, tension: 0.3, pointRadius: 3,
        }}, {{
          label: 'Failures',
          data: trend.map(d => d.failed),
          borderColor: '#f87171', backgroundColor: 'rgba(248,113,113,0.1)',
          fill: true, tension: 0.3, pointRadius: 3, yAxisID: 'y1',
        }}]
      }},
      options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        scales: {{
          y: {{ beginAtZero: false, min: 0, max: 105, title: {{ display: true, text: 'Pass Rate %', color: '#a0a0b0' }},
               ticks: {{ color: '#a0a0b0' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y1: {{ position: 'right', beginAtZero: true, title: {{ display: true, text: 'Failures', color: '#a0a0b0' }},
                ticks: {{ color: '#a0a0b0' }}, grid: {{ drawOnChartArea: false }} }},
          x: {{ ticks: {{ color: '#a0a0b0' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e4e4e4' }} }} }}
      }}
    }});

    new Chart(document.getElementById('chartDuration'), {{
      type: 'bar',
      data: {{
        labels,
        datasets: [{{
          label: 'Avg Duration (s)',
          data: trend.map(d => d.avg_duration),
          backgroundColor: 'rgba(96,165,250,0.6)', borderColor: '#60a5fa', borderWidth: 1,
        }}, {{
          label: 'Tests Run',
          data: trend.map(d => d.tests),
          type: 'line', borderColor: '#a78bfa',
          tension: 0.3, pointRadius: 3, yAxisID: 'y1',
        }}]
      }},
      options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        scales: {{
          y: {{ beginAtZero: true, title: {{ display: true, text: 'Duration (s)', color: '#a0a0b0' }},
               ticks: {{ color: '#a0a0b0' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y1: {{ position: 'right', beginAtZero: true, title: {{ display: true, text: 'Tests', color: '#a0a0b0' }},
                ticks: {{ color: '#a0a0b0' }}, grid: {{ drawOnChartArea: false }} }},
          x: {{ ticks: {{ color: '#a0a0b0' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e4e4e4' }} }} }}
      }}
    }});
  }}
}}
</script>
</body>
</html>"""


def main():
    print("╔═══════════════════════════════════════╗")
    print("║  CI Metrics Dashboard — Phase 4       ║")
    print("╚═══════════════════════════════════════╝")

    print(f"\n📊 Querying BigQuery ({GCP_PROJECT}.{BQ_DATASET})...")
    data = query_bigquery()

    s = data["summary"]
    print(f"   Pipelines: {s['pipelines']}")
    print(f"   Tests: {s['total_tests']} ({s['pass_rate']}% pass rate)")
    print(f"   Failures: {s['total_failed']}")
    print(f"   Trend days: {len(data['daily_trend'])}")
    print(f"   Recent failures: {len(data['recent_failures'])}")
    print(f"   Flaky tests: {len(data['flaky_tests'])}")

    print(f"\n📝 Generating HTML dashboard...")
    html = generate_html(data)

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    size_kb = len(html) / 1024
    print(f"   Written to {OUTPUT_PATH} ({size_kb:.1f} KB)")
    print(f"\n✅ Dashboard ready!")


if __name__ == "__main__":
    main()
