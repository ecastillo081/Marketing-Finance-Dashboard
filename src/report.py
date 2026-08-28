"""Generate the 3-page HTML case study and print it to PDF."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, create_string_object

from src.paths import REPO_ROOT
from src.sensitivity import CHANNEL_ORDER, SCENARIOS


CASE_DIR = REPO_ROOT / "case-study"
HTML_PATH = CASE_DIR / "marketing-investment-economics.html"
PDF_PATH = CASE_DIR / "Marketing_Investment_Economics_Case_Study.pdf"
GITHUB_URL = "https://github.com/ecastillo081/Marketing-Finance-Dashboard"

SHORT = {
    "Meta Ads": "Meta",
    "Google Ads - Search": "Search",
    "Google Ads - YouTube": "YouTube",
}


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _x(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}x"


def _payback(v) -> str:
    if v is None or pd.isna(v):
        return "-"
    return str(int(v))


def _row(alloc: pd.DataFrame, channel: str) -> pd.Series:
    return alloc.set_index("channel").loc[channel]


def _sens(df: pd.DataFrame, scenario: str, channel: str) -> pd.Series:
    return df[(df["scenario_id"] == scenario) & (df["channel"] == channel)].iloc[0]


def render_html(alloc: pd.DataFrame, sensitivity: pd.DataFrame) -> str:
    meta = _row(alloc, "Meta Ads")
    search = _row(alloc, "Google Ads - Search")
    yt = _row(alloc, "Google Ads - YouTube")
    total_spend = float(alloc["total_spend"].sum())
    total_nc = int(alloc["attributed_new_customers"].sum())

    def card(name: str, r: pd.Series) -> str:
        return f"""
        <article class="card">
          <div class="name">{name}</div>
          <div class="stat">{_money(r['total_spend'])} <span>{_pct(r['spend_mix_pct'])} of spend</span></div>
          <dl>
            <dt>Attributed new cust. proxy</dt><dd>{int(r['attributed_new_customers']):,}</dd>
            <dt>Blended CAC</dt><dd>{_money(r['blended_cac'])}</dd>
            <dt>Platform-attributed ROAS</dt><dd>{_x(r['platform_attributed_roas'], 2)}</dd>
          </dl>
        </article>"""

    def matrix_cell(scenario: str, channel: str) -> str:
        r = _sens(sensitivity, scenario, channel)
        pb = _payback(r["modeled_payback_month_index"])
        return f"{_x(r['weighted_lifetime_contribution_to_cac'], 2)} · m{pb}" if pb != "-" else f"{_x(r['weighted_lifetime_contribution_to_cac'], 2)} · none"

    matrix_rows = ""
    for sid, sname in SCENARIOS:
        cells = "".join(f"<td>{matrix_cell(sid, ch)}</td>" for ch in CHANNEL_ORDER)
        matrix_rows += f"<tr><th>{sname}</th>{cells}</tr>\n"

    s_arpu = _sens(sensitivity, "arpu_minus_20", "Google Ads - Search")
    s_cac = _sens(sensitivity, "cac_plus_20", "Google Ads - Search")
    yt_arpu = _sens(sensitivity, "arpu_minus_20", "Google Ads - YouTube")
    meta_arpu = _sens(sensitivity, "arpu_minus_20", "Meta Ads")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Marketing Investment Economics</title>
  <link rel="stylesheet" href="case-study.css" />
</head>
<body>
  <section class="page">
    <div class="kicker">GTM / Marketing Finance case study</div>
    <h1>Marketing Investment Economics</h1>
    <p class="subtitle">Evaluating acquisition efficiency, contribution payback, and capital-allocation risk</p>
    <div class="meta-row">
      <span>Efrain Castillo</span>
      <span class="badge">Self-directed portfolio project using synthetic data</span>
    </div>
    <div class="question">
      <strong>Business question.</strong>
      How should Finance evaluate where to test incremental marketing investment when channel acquisition
      costs, attributed returns, and modeled customer economics differ?
    </div>
    <h2>Acquisition efficiency varies materially across channels</h2>
    <div class="cards">
      {card("Meta Ads", meta)}
      {card("Google Ads - Search", search)}
      {card("Google Ads - YouTube", yt)}
    </div>
    <div class="charts-3">
      <img src="charts/spend_mix.png" alt="Channel spend mix" />
      <img src="charts/blended_cac.png" alt="Blended CAC by channel" />
      <img src="charts/attributed_roas.png" alt="Platform-attributed ROAS by channel" />
    </div>
    <p class="source">Source: validated local DuckDB build · synthetic fixtures · platform-attributed ROAS is not incremental return.</p>
    <div class="split">
      <div class="box">
        <h3>Synthetic observed fixture</h3>
        <ul>
          <li>Spend, attributed new-customer proxy</li>
          <li>Platform conversions / purchases</li>
          <li>Platform-attributed conversion value</li>
          <li>Blended CAC and platform-attributed ROAS</li>
        </ul>
      </div>
      <div class="box">
        <h3>Modeled assumptions / outputs</h3>
        <ul>
          <li>Shared retention curve and $50 ARPU</li>
          <li>Gross margin, refunds, fees, variable cost</li>
          <li>Contribution margin, lifetime contribution, payback</li>
          <li>Weighted lifetime contribution / CAC</li>
        </ul>
      </div>
    </div>
    <div class="callout">
      Portfolio fixture spend is {_money(total_spend)} across {total_nc:,} attributed new customers.
      Meta is {_pct(meta['spend_mix_pct'])} of spend. YouTube has the lowest blended CAC ({_money(yt['blended_cac'])});
      Search has the highest ({_money(search['blended_cac'])}). Platform-attributed ROAS is not profit and is not incremental return.
      These metrics identify differences in <strong>average acquisition efficiency</strong>, not marginal return on the next dollar.
    </div>
    <div class="footer">
      <span>Efrain Castillo · Self-directed portfolio project · Synthetic data</span>
      <span>1 / 3</span>
    </div>
  </section>

  <section class="page">
    <div class="kicker">Contribution economics</div>
    <h2>Contribution economics widen the channel differences</h2>
    <p>
      Lifetime figures are <strong>forward modeled</strong> over 38 months. They are not realized historical cohort performance.
      Retention and ARPU are shared assumptions; channel differences in modeled contribution also reflect finance-driver assumptions.
    </p>
    <div class="assumptions">
      <div><span class="lbl">ARPU</span><strong>$50 / month</strong> (flat)</div>
      <div><span class="lbl">Horizon</span><strong>38 months</strong> for every cohort</div>
      <div><span class="lbl">Retention</span><strong>Shared curve</strong> · 1.00 to 0.01</div>
      <div><span class="lbl">Finance drivers</span><strong>Channel-specific</strong> GM / refund / VC</div>
    </div>
    <div class="charts-2">
      <img src="charts/weighted_cm_cac.png" alt="Weighted modeled lifetime contribution over CAC" />
      <img src="charts/payback.png" alt="Modeled payback month" />
    </div>
    <p class="source">Source: validated local build · weighted = (customers x modeled CM per customer) / spend · payback month 0 = acquisition month.</p>
    <table>
      <thead>
        <tr>
          <th>Channel</th>
          <th>Modeled lifetime CM / customer</th>
          <th>Weighted CM / CAC</th>
          <th>Modeled payback month</th>
          <th>Cohorts not paying back</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>YouTube</td>
          <td>{_money(yt['modeled_lifetime_contribution_per_customer'])}</td>
          <td>{_x(yt['modeled_lifetime_contribution_to_cac_weighted'])}</td>
          <td>{_payback(yt['modeled_payback_month_index'])}</td>
          <td>{int(yt['cohorts_never_pay_back'])} / {int(yt['acquisition_cohorts'])}</td>
        </tr>
        <tr>
          <td>Meta</td>
          <td>{_money(meta['modeled_lifetime_contribution_per_customer'])}</td>
          <td>{_x(meta['modeled_lifetime_contribution_to_cac_weighted'])}</td>
          <td>{_payback(meta['modeled_payback_month_index'])}</td>
          <td>{int(meta['cohorts_never_pay_back'])} / {int(meta['acquisition_cohorts'])}</td>
        </tr>
        <tr>
          <td>Search</td>
          <td>{_money(search['modeled_lifetime_contribution_per_customer'])}</td>
          <td>{_x(search['modeled_lifetime_contribution_to_cac_weighted'])}</td>
          <td>{_payback(search['modeled_payback_month_index'])}</td>
          <td>{int(search['cohorts_never_pay_back'])} / {int(search['acquisition_cohorts'])}</td>
        </tr>
      </tbody>
    </table>
    <div class="callout">
      YouTube's strongest modeled economics combine low blended CAC with slightly better assumed contribution
      (higher GM, lower refunds and variable cost). Meta combines the greatest fixture scale with stronger modeled
      economics than Search. Search has the thinnest modeled cushion: {_x(search['modeled_lifetime_contribution_to_cac_weighted'])}
      and payback month {int(search['modeled_payback_month_index'])}, with
      {int(search['cohorts_never_pay_back'])} of {int(search['acquisition_cohorts'])} acquisition cohorts not paying back
      within 38 months. Average modeled economics do not establish that additional spend can be placed at the same CAC.
    </div>
    <div class="footer">
      <span>Python · DuckDB · SQL · pandas · matplotlib</span>
      <span>2 / 3</span>
    </div>
  </section>

  <section class="page">
    <div class="kicker">Capital allocation under uncertainty</div>
    <h2>Average economics identify test priorities, not automatic budget shifts</h2>
    <p>
      Downside cases recompute the contribution waterfall. They do not apply cosmetic percentages to the ratio.
      There is no marginal-response curve in this fixture, so a “move spend and keep the same return” scenario is not valid.
    </p>
    <div class="chart-wide">
      <img src="charts/sensitivity_cm_cac.png" alt="Sensitivity matrix of weighted modeled lifetime contribution over CAC" />
    </div>
    <table>
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Meta (CM/CAC · payback)</th>
          <th>Search (CM/CAC · payback)</th>
          <th>YouTube (CM/CAC · payback)</th>
        </tr>
      </thead>
      <tbody>
        {matrix_rows}
      </tbody>
    </table>
    <p class="note">
      Search is the most fragile: under ARPU -20% weighted CM/CAC falls to {_x(s_arpu['weighted_lifetime_contribution_to_cac'], 2)}
      (payback month {_payback(s_arpu['modeled_payback_month_index'])}).
      CAC +20% leaves Search at {_x(s_cac['weighted_lifetime_contribution_to_cac'], 2)}.
      YouTube remains above {_x(yt_arpu['weighted_lifetime_contribution_to_cac'], 2)} even with ARPU -20%, but is only {_pct(yt['spend_mix_pct'])} of fixture spend.
      Meta stays above {_x(meta_arpu['weighted_lifetime_contribution_to_cac'], 2)} in that case while already representing {_pct(meta['spend_mix_pct'])} of spend.
    </p>
    <div class="split">
      <div class="box">
        <h3>What Finance can say now</h3>
        <ul>
          <li>Search has the least downside cushion in the modeled economics.</li>
          <li>YouTube warrants incremental testing because baseline modeled economics are strongest — not because scale is proven.</li>
          <li>Meta warrants continued scrutiny because it is already {_pct(meta['spend_mix_pct'])} of fixture spend.</li>
          <li>Assumption sensitivity materially changes investment attractiveness, especially for Search.</li>
        </ul>
      </div>
      <div class="box">
        <h3>What Finance needs before scaling</h3>
        <ul>
          <li>Marginal CAC and spend capacity / saturation</li>
          <li>Incremental contribution, not only platform-attributed ROAS</li>
          <li>Attribution overlap and cannibalization</li>
          <li>Realized retention, ARPU, and customer quality by channel</li>
        </ul>
      </div>
    </div>
    <h3>Management actions</h3>
    <ol class="actions">
      <li>Set channel investment guardrails using contribution-margin payback and downside cases, not ROAS alone.</li>
      <li>Prioritize incremental testing where average modeled economics are strongest, while explicitly testing marginal CAC and capacity.</li>
      <li>Investigate Search cohorts that do not pay back within the 38-month modeled horizon before adding spend.</li>
      <li>Replace shared ARPU/retention assumptions with observed channel and customer-quality data when enough history exists.</li>
    </ol>
    <p class="limits">
      <strong>Limitations.</strong> Synthetic ad fixtures; sparse sampled dates, not a continuous daily panel; platform attribution is not causal incrementality;
      ARPU and retention are modeled; 38-month forward horizon; Google campaign taxonomy is fixture-limited; no marginal-response or saturation data.
    </p>
    <div class="footer">
      <span>Efrain Castillo · <a href="{GITHUB_URL}">{GITHUB_URL.replace('https://','')}</a></span>
      <span>3 / 3</span>
    </div>
  </section>
</body>
</html>
"""


def _find_browser() -> Path:
    pf = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    pf86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        pf / "Google" / "Chrome" / "Application" / "chrome.exe",
        local / "Google" / "Chrome" / "Application" / "chrome.exe",
        pf / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        pf86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Chrome or Edge is required to print the case-study PDF.")


def export_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = _find_browser()
    html_uri = html_path.resolve().as_uri()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-first-run",
        "--no-default-browser-check",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        html_uri,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    for _ in range(20):
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            break
        time.sleep(0.2)
    if not pdf_path.exists():
        raise RuntimeError(f"Browser did not write PDF to {pdf_path}")


def set_pdf_metadata(pdf_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": "Marketing Investment Economics",
            "/Author": "Efrain Castillo",
            "/Subject": "Self-directed Marketing Finance portfolio case study using synthetic data.",
        }
    )
    info = writer._info
    info[NameObject("/Creator")] = create_string_object("Efrain Castillo")
    info[NameObject("/Producer")] = create_string_object("Efrain Castillo")
    tmp = pdf_path.with_suffix(".meta.pdf")
    with tmp.open("wb") as f:
        writer.write(f)
    tmp.replace(pdf_path)


def generate_report(alloc: pd.DataFrame, sensitivity: pd.DataFrame) -> dict[str, str]:
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(render_html(alloc, sensitivity), encoding="utf-8")
    export_pdf(HTML_PATH, PDF_PATH)
    set_pdf_metadata(PDF_PATH)
    reader = PdfReader(str(PDF_PATH))
    pages = len(reader.pages)
    meta = reader.metadata or {}
    return {
        "html": str(HTML_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "pdf": str(PDF_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "pages": str(pages),
        "title": str(meta.get("/Title", "")),
        "author": str(meta.get("/Author", "")),
        "github": GITHUB_URL,
    }
