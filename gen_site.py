#!/usr/bin/env python3
"""Build the dated public sample from pinned snapshot files.

No network calls, database mutations, emails, or publication occur here.
The snapshot preserves the September 3 sample; September 20 corrections clarify
product identity and unavailable services. It is not a current market feed.
Do not advertise subscriber delivery, buyers, price parity, or historical depth
without supporting data and a working delivery path. Refreshing this sample
requires revalidating dates, source definitions and the snapshot manifest.
Preserve the existing exclusion of Enviva from promotional sample rows.
"""
from __future__ import annotations

import html as html_mod
import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
EX = HERE / "snapshot"
manifest = json.loads((EX / "manifest.json").read_text())
for filename, expected in manifest.items():
    if hashlib.sha256((EX / filename).read_bytes()).hexdigest() != expected:
        raise ValueError(f"Snapshot changed: {filename}. Revalidate before publishing.")
summary = json.loads((EX / "summary.json").read_text())
SAMPLE = HERE / "sample"
SAMPLE.mkdir(exist_ok=True)

EMAIL = "njjones1999@gmail.com"
COMPANY = "Scriptores Helm LLC"
SOURCES = "EIA · DEPV · BaltPool · ENplus · UN Comtrade"


def mailto(subject: str, body: str = "") -> str:
    from urllib.parse import quote
    s = quote(subject)
    b = quote(body)
    return f"mailto:{EMAIL}?subject={s}" + (f"&body={b}" if body else "")


# ---------------------------------------------------------------- formatting
def fi(n) -> str:
    """1,234,567"""
    return f"{float(n):,.0f}"


def f2(n) -> str:
    return f"{float(n):,.2f}"


def fm(n) -> str:
    """$1,342.1M style for big money"""
    return f"${float(n)/1e6:,.1f}M"


def pct(a, b) -> float:
    return (a / b - 1) * 100


def delta_html(p: float) -> str:
    arrow = "▲" if p >= 0 else "▼"
    color = "#39b54a" if p >= 0 else "#d95c4a"
    return f'<span style="color:{color};font-weight:600">{arrow} {abs(p):.1f}%</span>'


def esc(s) -> str:
    return html_mod.escape(str(s))


# ---------------------------------------------------------------- load data
mills = pd.read_csv(EX / "mills_current.csv")
mills_ne = mills[~mills.company.str.contains("enviva", case=False)]
top10 = mills_ne.sort_values("annual_capacity_tpy", ascending=False).head(10)
top15 = mills_ne.sort_values("annual_capacity_tpy", ascending=False).head(15)
idle = mills[mills.status != "Currently Operating"]
region_tbl = mills.groupby("region").agg(n=("company", "size"), cap=("annual_capacity_tpy", "sum"))

eb = pd.read_csv(EX / "eu_benchmarks.csv")
depv = eb[eb["index"] == "DEPV pelletpreis"].copy()
bp = eb[eb["index"] == "BaltPool spot"].copy().reset_index(drop=True)
DEPV_LATEST = depv.period.max()
DEPV_PREV = sorted(depv.period.unique())[-2]
bp_last = bp.iloc[-1]
bp_prev = bp.iloc[-2]
BP_WOW = pct(bp_last.value, bp_prev.value)

ep = pd.DataFrame(summary["exports"])
en_counts = pd.DataFrame([summary["producer_counts"]])
en_active = pd.DataFrame([summary["active_producers"]])
YTD_EXP_VALUE = float(ep.value_usd.astype(float).sum())
YTD_EXP_QTY = float(ep.quantity_tons.sum())
YTD_EXP_PRICE = YTD_EXP_VALUE / YTD_EXP_QTY

exd = pd.read_csv(EX / "export_destinations.csv")
exd = exd[exd.source == "comtrade_hs440131"].copy()
EX_YEAR = int(exd.period.max())
e24 = exd[(exd.period == EX_YEAR) & (exd.destination_country != "World")].copy()
e24["value_usd"] = e24.value_usd_cents / 100
e24["usd_per_t"] = e24.value_usd / e24.quantity_tons
e24 = e24.sort_values("quantity_tons", ascending=False)
world = exd[(exd.period == EX_YEAR) & (exd.destination_country == "World")].iloc[0]
TOP_DEST = e24.head(4)

ph = pd.read_csv(EX / "price_history_10y.csv", dtype={"period": str})
ph["period"] = ph.period.astype(str).str.zfill(2)
LAST_M, PREV_M = "05", "04"  # Pinned 2026 sample, not automatic latest-month detection
MONTHS = dict([("01", "Jan"), ("02", "Feb"), ("03", "Mar"), ("04", "Apr"), ("05", "May")])
EIA_RELEASE = "August 13, 2026"


def rows(kind, period):
    return ph[(ph.kind == kind) & (ph.period == period)]


def us_prod(period):
    t = rows("production_tons", period)
    t = t[t.region == "U.S. Total"]
    prem = t[t.series_or_feedstock.str.contains("premium")].production_tons.sum()
    util = t[t.series_or_feedstock.str.contains("utility")].production_tons.sum()
    return prem, util


prem_l, util_l = us_prod(LAST_M)
prem_p, util_p = us_prod(PREV_M)
prod_l, prod_p = prem_l + util_l, prem_p + util_p
YTD_PREM = sum(us_prod(m)[0] for m in ["01", "02", "03", "04", "05"])
YTD_UTIL = sum(us_prod(m)[1] for m in ["01", "02", "03", "04", "05"])
YTD_PROD = YTD_PREM + YTD_UTIL

exp_l = rows("exports", LAST_M).iloc[0]
exp_p = rows("exports", PREV_M).iloc[0]


def fs(period):
    r = rows("feedstock_cost", period).set_index("series_or_feedstock").price / 100
    return r


fs_l, fs_p = fs(LAST_M), fs(PREV_M)

DEPV6_L = depv[(depv.period == DEPV_LATEST) & (depv.series_or_country == "DEPV 6t")].value.iloc[0]
DEPV6_P = depv[(depv.period == DEPV_PREV) & (depv.series_or_country == "DEPV 6t")].value.iloc[0]
DEPV26_L = depv[(depv.period == DEPV_LATEST) & (depv.series_or_country == "DEPV 26t")].value.iloc[0]
DEPV26_P = depv[(depv.period == DEPV_PREV) & (depv.series_or_country == "DEPV 26t")].value.iloc[0]
depv_nat = depv[depv.series_or_country.str.startswith("DEPV ")].copy()

TOTAL_CAP = int(mills.annual_capacity_tpy.sum())
N_MILLS = len(mills)
N_OPERATING = int((mills.status == "Currently Operating").sum())
N_EN = int(en_counts.n.iloc[0])
N_EN_ACTIVE = int(en_active.n.iloc[0])
N_EN_COUNTRIES = int(en_counts.c.iloc[0])

MONTH_NAME = {"01": "January", "02": "February", "03": "March", "04": "April", "05": "May"}
LATEST_US_MONTH = f"{MONTH_NAME[LAST_M]} 2026"
PREV_US_MONTH = f"{MONTH_NAME[PREV_M]} 2026"
AS_OF = (f"EIA-63C data through {LATEST_US_MONTH} (report released {EIA_RELEASE}) · "
         f"DEPV {DEPV_LATEST} · BaltPool {bp_last.period} · UN Comtrade {EX_YEAR} annual · "
         f"sample inputs fetched 2026-09-03; descriptions corrected 2026-09-20")

# ---------------------------------------------------------------- styles
CSS = """
:root{
  --bg:#131512; --panel:#1b1e19; --panel2:#22261f; --line:#2c3129; --line2:#3a4034;
  --ink:#e8eae4; --mut:#9aa392; --dim:#6d7566;
  --amber:#F0A400; --amber-dim:#8a6100; --green:#39b54a; --red:#d95c4a;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--amber);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:980px;margin:0 auto;padding:0 18px}
header.site{border-bottom:1px solid var(--line);background:#161913}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:10px;padding-top:14px;padding-bottom:14px}
.brand{font-weight:800;letter-spacing:.14em;font-size:14px;color:var(--amber)}
.brand small{display:block;letter-spacing:.05em;color:var(--mut);font-weight:500;font-size:11px}
nav a{color:var(--mut);font-size:13px;margin-left:18px}
nav a:hover{color:var(--amber);text-decoration:none}
.hero{padding:56px 0 30px}
.kicker{color:var(--amber);font-size:12px;font-weight:700;letter-spacing:.18em;text-transform:uppercase}
h1{font-size:34px;line-height:1.2;margin:12px 0 14px;font-weight:800}
.sub{color:var(--mut);font-size:18px;max-width:700px}
h2{font-size:22px;margin:0 0 6px}
h3{font-size:16px;margin:0 0 4px}
.sect{padding:34px 0;border-top:1px solid var(--line)}
.sect .lead{color:var(--mut);max-width:760px;margin:0 0 18px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:26px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:24px;color:var(--amber);font-weight:800}
.stat span{color:var(--mut);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px}
.card h3{color:var(--ink)}
.card p{color:var(--mut);font-size:14px;margin:8px 0 0}
.card .tag{display:inline-block;font-size:11px;color:var(--amber);border:1px solid var(--amber-dim);
  border-radius:20px;padding:2px 10px;margin-bottom:8px;letter-spacing:.08em;text-transform:uppercase}
.tblwrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;margin:14px 0 6px}
table{border-collapse:collapse;width:100%;font-size:14px}
th{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--mut);
  text-align:left;padding:10px 12px;border-bottom:1px solid var(--line2);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid #23271f;white-space:nowrap}
tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:#171a14}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
td.strong{font-weight:600}
.caption{color:var(--dim);font-size:12px;margin:2px 0 20px}
.pill{display:inline-block;font-size:11px;border-radius:20px;padding:1px 9px;font-weight:600}
.pill.ok{color:var(--green);border:1px solid #2c5c33}
.pill.idle{color:var(--mut);border:1px solid var(--line2)}
.btn{display:inline-block;background:var(--amber);color:#131512;font-weight:700;
  border-radius:8px;padding:12px 20px;font-size:15px}
.btn:hover{filter:brightness(1.08);text-decoration:none}
.btn.ghost{background:transparent;color:var(--amber);border:1px solid var(--amber-dim)}
.btnrow{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}
.price{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px}
.price .amt{font-size:30px;font-weight:800;color:var(--amber)}
.price .per{color:var(--mut);font-size:13px}
.price ul{margin:12px 0 16px;padding-left:18px;color:var(--mut);font-size:14px}
.price li{margin:5px 0}
.price .pick{color:var(--amber);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  border:1px solid var(--amber-dim);border-radius:20px;padding:2px 10px;display:inline-block;margin-bottom:8px}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;align-items:start}
.alerts{list-style:none;margin:14px 0;padding:0}
.alerts li{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--amber);
  border-radius:8px;padding:12px 14px;margin-bottom:10px;font-size:14px;color:var(--mut)}
.alerts li b{color:var(--ink)}
footer.site{border-top:1px solid var(--line);margin-top:30px;padding:26px 0 40px;color:var(--dim);font-size:13px}
footer.site a{color:var(--mut)}
.note{background:var(--panel2);border:1px dashed var(--line2);border-radius:8px;
  padding:12px 14px;color:var(--mut);font-size:13px;margin:16px 0}
@media(max-width:720px){
  h1{font-size:26px}.hero{padding:36px 0 20px}
  nav a{margin-left:12px;font-size:12px}
  .btn{display:block;text-align:center;margin-bottom:10px}
  .btnrow{display:block}
}
"""

FOOTER = f"""
<footer class="site"><div class="wrap">
  <b style="color:var(--mut)">{COMPANY}</b> · Mississippi, USA<br>
  Dated public-source sample: {SOURCES}. Automated delivery and paid orders are unavailable.<br>
  Contact: <a href="mailto:{EMAIL}">{EMAIL}</a> ·
  Sample pages: <a href="sample/sample-digest.html">digest</a> ·
  <a href="sample/sample-milldb.html">mill DB</a> ·
  <a href="sample/sample-eubench.html">EU benchmarks</a>
</div></footer>
"""


def page(title: str, body: str, sample: bool = False) -> str:
    prefix = "../" if sample else ""
    nav = f"""
    <nav>
      <a href="{prefix}index.html">Overview</a>
      <a href="{prefix}sample/sample-digest.html">Sample digest</a>
      <a href="{prefix}sample/sample-milldb.html">Sample mill DB</a>
      <a href="{prefix}sample/sample-eubench.html">Sample EU benchmarks</a>
      <a href="{prefix}index.html#pricing">Availability</a>
    </nav>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <div class="brand">PELLET MARKET MONITOR<small>US wood-pellet market intelligence</small></div>
  {nav}
</div></header>
<div class="wrap"><div class="note"><b>Dated sample, corrected September 20, 2026.</b> Original data snapshot: September 3. Paid orders and automated subscriber delivery are unavailable. Earlier wording incorrectly described wood chips as a pellet benchmark and implied subscriber alerts had been sent.</div></div>
{body}
{SOURCE_NOTES}
{FOOTER.replace('sample/', prefix + 'sample/')}
</body>
</html>"""


SOURCE_NOTES = '\n<section class="sect"><div class="wrap"><h2>Sources and definitions</h2>\n<p><a href="https://www.eia.gov/biofuels/biomass/?year=2026&amp;month=5">EIA May 2026 report</a>: Tables 1, 3, 4 and 8; st means short tons. EIA export value shown here is calculated as reported quantity × reported average price.</p>\n<p><a href="https://www.depv.de/pelletpreis/">DEPV contract-price definition</a>: ENplus A1, loose blown-in pellets, delivery within 50 km, incidental costs included, VAT excluded. 3/6/26 t are order quantities, not bag sizes.</p>\n<p><a href="https://www.baltpool.eu/wp-content/uploads/2026/06/baltpool-index-api-documentation.pdf">Baltpool index API reference</a>: displayed series uses type=spot and country=lt, in EUR/MWh. The separate wood-pellet type is wood_pellets_spot.</p>\n<p><a href="https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=842&amp;period=2024&amp;cmdCode=440131&amp;flowCode=X">UN Comtrade query</a>: US exports, 2024, HS 440131. Net weight divided by 1,000 yields metric tonnes; customs value divided by that weight yields unit value. Country labels beyond this selected table remain under review.</p>\n<p>Different periods, products and units remain separate. These tables do not establish a current purchase price, landed cost, arbitrage margin or list of buyers. Older source data may be revised by its publisher.</p>\n</div></section>\n'

# ================================================================ INDEX.HTML
def mill_rows(df) -> str:
    out = []
    for _, r in df.iterrows():
        st = ('<span class="pill ok">Operating</span>'
              if r.status == "Currently Operating"
              else '<span class="pill idle">Idle</span>')
        out.append(
            f"<tr><td class='strong'>{esc(r.company)}</td><td>{esc(r.state)}</td>"
            f"<td>{esc(r.region)}</td><td>{st}</td>"
            f"<td class='num'>{fi(r.annual_capacity_tpy)}</td></tr>")
    return "\n".join(out)


def dest_rows() -> str:
    out = []
    for _, r in TOP_DEST.iterrows():
        out.append(f"<tr><td class='strong'>{esc(r.destination_country)}</td>"
                   f"<td class='num'>{fi(r.quantity_tons)}</td>"
                   f"<td class='num'>{fm(r.value_usd)}</td>"
                   f"<td class='num'>${f2(r.usd_per_t)}</td></tr>")
    out.append(f"<tr><td class='strong'>World (all destinations)</td>"
               f"<td class='num'>{fi(world.quantity_tons)}</td>"
               f"<td class='num'>{fm(world.value_usd_cents/100)}</td>"
               f"<td class='num'>${world.value_usd_cents/100/world.quantity_tons:,.2f}</td></tr>")
    return "\n".join(out)


def bp_rows(n=6) -> str:
    out = []
    tail = bp.tail(n).reset_index(drop=True)
    for i, r in tail.iterrows():
        if i == 0:
            d = '<span style="color:var(--dim)">—</span>'
        else:
            p = tail.value[i - 1]
            d = delta_html(pct(r.value, p))
        out.append(f"<tr><td>{esc(r.period)}</td><td class='num strong'>€{r.value:,.2f}</td>"
                   f"<td class='num'>{d}</td></tr>")
    return "\n".join(out)


def depv_regional_rows() -> str:
    out = []
    reg = depv[(depv.period == DEPV_LATEST) & (~depv.series_or_country.str.startswith("DEPV "))]
    for _, r in reg.iterrows():
        out.append(f"<tr><td class='strong'>{esc(r.series_or_country)}</td>"
                   f"<td class='num'>€{r.value:,.2f}</td></tr>")
    return "\n".join(out)


index_body = f"""
<section class="hero"><div class="wrap">
  <div class="kicker">Scriptores Helm · research prototype</div>
  <h1>Wood-pellet market data,<br>with the source context attached.</h1>
  <p class="sub">Explore a dated sample of US production, feedstock costs, exports and German pellet prices. Lithuanian wood-chip prices are included separately as biomass context.</p>
  <div class="note"><b>Sample only.</b> These pages retain data collected September 3, 2026; they are not a live feed. Descriptions were corrected September 20. Paid orders, weekly email delivery and automated alerts are unavailable.</div>
  <div class="btnrow"><a class="btn" href="sample/sample-digest.html">Read the free sample</a>
  <a class="btn ghost" href="#pricing">Product availability</a></div>
</div></section>
<section class="sect"><div class="wrap">
  <h2>How to read this sample</h2>
  <p class="lead">Use it to inspect reported supply, costs and trade. Each series has its own reporting period and definition; this is not a landed-cost or export-parity calculator.</p>
  <div class="cards">
    <div class="card"><h3>US monthly statistics</h3><p>EIA production, feedstock costs and export averages. Reporting lags mean these are historical observations, not current supplier quotes.</p></div>
    <div class="card"><h3>Different products and price bases</h3><p>German delivered pellet prices and Lithuanian wood-chip prices are separate series. Currency, mass, energy content, grade and delivery costs have not been normalized for comparison.</p></div>
    <div class="card"><h3>Trade destinations and suppliers</h3><p>UN Comtrade describes country-level exports. ENplus lists certified producers; it does not establish which companies buy US pellets.</p></div>
  </div>
</div></section>
<section class="sect" id="data"><div class="wrap">
  <h2>The dated sample</h2>
  <p class="lead">Source data retained for this sample ( {esc(AS_OF)}).
  Full pages: <a href="sample/sample-digest.html">sample digest</a> ·
  <a href="sample/sample-milldb.html">sample mill database</a> ·
  <a href="sample/sample-eubench.html">sample EU benchmarks</a>.</p>

  <h3>US pellet mills — top {len(top10)} by listed capacity <span style="color:var(--dim);font-weight:400">(of {N_MILLS} tracked, {N_OPERATING} operating)</span></h3>
  <div class="tblwrap"><table>
    <thead><tr><th>Mill</th><th>State</th><th>Region</th><th>Status</th><th class="num">Capacity (tons/yr)</th></tr></thead>
    <tbody>
{mill_rows(top10)}
    </tbody>
  </table></div>
  <p class="caption">Source: EIA-63C Table 1, fetched 2026-09-03. Selected mills exclude Enviva; totals cover all listed mills. Status is as reported in that snapshot.</p>

  <h3>US production &amp; exports — {esc(LATEST_US_MONTH)} <span style="color:var(--dim);font-weight:400">(sample reporting month; prior {esc(PREV_US_MONTH)} for comparison)</span></h3>
  <div class="tblwrap"><table>
    <thead><tr><th>Series</th><th class="num">{esc(LATEST_US_MONTH)}</th><th class="num">{esc(PREV_US_MONTH)}</th><th class="num">Change</th></tr></thead>
    <tbody>
      <tr><td class="strong">US production, total</td>
          <td class="num">{fi(prod_l)} st</td><td class="num">{fi(prod_p)} st</td>
          <td class="num">{delta_html(pct(prod_l, prod_p))}</td></tr>
      <tr><td class="strong">&nbsp;&nbsp;premium/standard</td>
          <td class="num">{fi(prem_l)} st</td><td class="num">{fi(prem_p)} st</td>
          <td class="num">{delta_html(pct(prem_l, prem_p))}</td></tr>
      <tr><td class="strong">&nbsp;&nbsp;utility</td>
          <td class="num">{fi(util_l)} st</td><td class="num">{fi(util_p)} st</td>
          <td class="num">{delta_html(pct(util_l, util_p))}</td></tr>
      <tr><td class="strong">Exports, all destinations</td>
          <td class="num">{fi(exp_l.production_tons)} st</td>
          <td class="num">{fi(exp_p.production_tons)} st</td>
          <td class="num">{delta_html(pct(exp_l.production_tons, exp_p.production_tons))}</td></tr>
      <tr><td class="strong">Export average price</td>
          <td class="num">${exp_l.price/100:,.2f}/st</td>
          <td class="num">${exp_p.price/100:,.2f}/st</td>
          <td class="num">{delta_html(pct(exp_l.price, exp_p.price))}</td></tr>
    </tbody>
  </table></div>
  <p class="caption">Year-to-date ({MONTH_NAME['01']}–{MONTH_NAME[LAST_M]} 2026): {fi(YTD_PROD)} st produced ·
  {fi(YTD_EXP_QTY)} st exported · ${YTD_EXP_VALUE/1e6:,.1f}M export value · ${YTD_EXP_PRICE:,.2f}/st average.
  Source: EIA-63C Tables 3/4/8.</p>

  <h3>German pellets and separate wood-chip context — sample periods</h3>
  <div class="cards">
    <div class="card">
      <h3>DEPV — German delivered pellet contract prices (net), {esc(DEPV_LATEST)}</h3>
      <div class="tblwrap" style="border:none;margin:0;background:transparent"><table>
        <thead><tr><th>Series</th><th class="num">€/metric tonne</th><th class="num">MoM</th></tr></thead>
        <tbody>
          <tr><td class="strong">DEPV 6t (national)</td><td class="num">{DEPV6_L:,.2f}</td>
              <td class="num">{delta_html(pct(DEPV6_L, DEPV6_P))}</td></tr>
          <tr><td class="strong">DEPV 26t (national)</td><td class="num">{DEPV26_L:,.2f}</td>
              <td class="num">{delta_html(pct(DEPV26_L, DEPV26_P))}</td></tr>
        </tbody>
      </table></div>
      <p class="caption">vs {esc(DEPV_PREV)}: 6t {DEPV6_P:,.2f} · 26t {DEPV26_P:,.2f}.
      Source: DEPV pelletpreis.</p>
    </div>
    <div class="card">
      <h3>Baltpool — Lithuanian wood-chip SPOT</h3>
      <div class="tblwrap" style="border:none;margin:0;background:transparent"><table>
        <thead><tr><th>Week</th><th class="num">€/MWh</th><th class="num">WoW</th></tr></thead>
        <tbody>
{bp_rows(6)}
        </tbody>
      </table></div>
      <p class="caption">Sample observation {esc(bp_last.period)}: €{bp_last.value:,.2f}/MWh.
      Source: BaltPool spot.</p>
    </div>
  </div>

  <h3>Top US export destinations, {EX_YEAR} <span style="color:var(--dim);font-weight:400">(UN Comtrade, HS 4401.31)</span></h3>
  <div class="tblwrap"><table>
    <thead><tr><th>Destination</th><th class="num">Volume (metric tonnes)</th><th class="num">Value</th><th class="num">Customs unit value ($/t)</th></tr></thead>
    <tbody>
{dest_rows()}
    </tbody>
  </table></div>
  <p class="caption">{EX_YEAR} annual totals for HS 440131 only. Volume is metric tonnes; unit value is reported customs value divided by net weight, not a purchase quote. Country totals do not identify individual buyers.</p>
</div></section>

<section class="sect" id="pricing"><div class="wrap">
  <h2>Product availability</h2>
  <p class="lead">The sample is free to read. Paid orders are paused while source definitions and delivery are validated.</p>
  <div class="cards">
    <div class="card"><h3>Free sample · available</h3><p>Read the digest, mill extract and benchmark definitions. The sample is a dated snapshot, not an ongoing service.</p></div>
    <div class="card"><h3>Subscription · unavailable</h3><p>The previously advertised $49/month or $499/year service is not accepting orders. Weekly subscriber emails and automated alerts have not been implemented.</p></div>
    <div class="card"><h3>Dataset pack · paused</h3><p>The previously advertised $99 pack is under review. Historical coverage, product labels and delivery contents must be confirmed before a sale.</p></div>
  </div>
  <div class="btnrow"><a class="btn" href="{mailto('Sample feedback — Pellet Market Monitor', 'Which table would help your work, and what information is missing?')}">Share sample feedback</a></div>
</div></section>
"""

index_html = page("Pellet Market Monitor — dated research sample", index_body)

# ================================================================ SAMPLE DIGEST
fs_rows_html = []
for name in ["Roundwood/pulpwood", "Sawmill residuals", "Wood product manufacturing residuals",
             "Other residuals"]:
    if name in fs_l.index:
        cur = fs_l[name]
        if name in fs_p.index and not pd.isna(fs_p[name]):
            d = delta_html(pct(cur, fs_p[name]))
            prev_s = f"${fs_p[name]:,.2f}"
        else:
            d = '<span style="color:var(--dim)">withheld by EIA</span>'
            prev_s = "—"
        fs_rows_html.append(
            f"<tr><td class='strong'>{esc(name)}</td><td class='num'>${cur:,.2f}/st</td>"
            f"<td class='num'>{prev_s}</td><td class='num'>{d}</td></tr>")
FS_ROWS = "\n".join(fs_rows_html)

reg_rows = []
for region in ["East", "South", "West"]:
    r = rows("production_tons", LAST_M)
    r = r[r.region == region]
    prem = r[r.series_or_feedstock.str.contains("premium")].production_tons.sum()
    util = r[r.series_or_feedstock.str.contains("utility")].production_tons.sum()
    if prem == 0 and util == 0:
        continue
    reg_rows.append(f"<tr><td class='strong'>{esc(region)}</td>"
                    f"<td class='num'>{fi(prem) if prem else '—'}</td>"
                    f"<td class='num'>{fi(util) if util else '—'}</td>"
                    f"<td class='num'>{fi(prem+util)}</td></tr>")
REG_ROWS = "\n".join(reg_rows)

sample_digest_body = f"""
<section class="hero" style="padding-bottom:8px"><div class="wrap">
  <div class="kicker">Sample · historical data digest</div>
  <h1 style="font-size:28px">Sample digest — September 3, 2026 snapshot</h1>
  <p class="sub" style="font-size:15px">Historical source data assembled into a sample; not a live feed. {esc(AS_OF)}.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">

  <div class="note"><b>Historical movement, not a sent alert:</b> Lithuanian wood-chip SPOT
  €{bp_prev.value:,.2f} → €{bp_last.value:,.2f}/MWh ({delta_html(BP_WOW)}).
  This is a wood-chip series, not a pellet price. No subscriber alert was sent; automated alerts are not implemented.</div>

  <h2>1 · US production — {esc(LATEST_US_MONTH)}</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Region</th><th class="num">Premium/standard (st)</th>
      <th class="num">Utility (st)</th><th class="num">Total (st)</th></tr></thead>
    <tbody>
{REG_ROWS}
      <tr><td class="strong">U.S. Total</td><td class="num">{fi(prem_l)}</td>
          <td class="num">{fi(util_l)}</td><td class="num">{fi(prod_l)}</td></tr>
    </tbody>
  </table></div>
  <p class="caption">Month-over-month: {fi(prod_l)} st vs {fi(prod_p)} st in {esc(PREV_US_MONTH)}
  ({delta_html(pct(prod_l, prod_p))}). YTD {MONTH_NAME['01']}–{MONTH_NAME[LAST_M]} 2026: {fi(YTD_PROD)} st.
  Source: EIA-63C Table 4.</p>

  <h2>2 · Feedstock costs — {esc(LATEST_US_MONTH)}</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Feedstock</th><th class="num">{esc(LATEST_US_MONTH)}</th>
      <th class="num">{esc(PREV_US_MONTH)}</th><th class="num">Change</th></tr></thead>
    <tbody>
{FS_ROWS}
    </tbody>
  </table></div>
  <p class="caption">US average cost per short ton. "Other residuals" withheld (W) by EIA for
  the months shown — reported as withheld, never imputed. Source: EIA-63C Table 3.</p>

  <h2>3 · Exports — {esc(LATEST_US_MONTH)}</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Series</th><th class="num">{esc(LATEST_US_MONTH)}</th>
      <th class="num">{esc(PREV_US_MONTH)}</th><th class="num">Change</th></tr></thead>
    <tbody>
      <tr><td class="strong">Volume (all destinations)</td>
          <td class="num">{fi(exp_l.production_tons)} st</td>
          <td class="num">{fi(exp_p.production_tons)} st</td>
          <td class="num">{delta_html(pct(exp_l.production_tons, exp_p.production_tons))}</td></tr>
      <tr><td class="strong">Average price</td>
          <td class="num">${exp_l.price/100:,.2f}/st</td>
          <td class="num">${exp_p.price/100:,.2f}/st</td>
          <td class="num">{delta_html(pct(exp_l.price, exp_p.price))}</td></tr>
      <tr><td class="strong">Export value</td>
          <td class="num">${float(ep[ep.period=='05'].value_usd.iloc[0])/1e6:,.1f}M</td>
          <td class="num">${float(ep[ep.period=='04'].value_usd.iloc[0])/1e6:,.1f}M</td>
          <td class="num">{delta_html(pct(float(ep[ep.period=='05'].value_usd.iloc[0]), float(ep[ep.period=='04'].value_usd.iloc[0])))}</td></tr>
    </tbody>
  </table></div>
  <p class="caption">YTD {MONTH_NAME['01']}–{MONTH_NAME[LAST_M]} 2026: {fi(YTD_EXP_QTY)} st ·
  ${YTD_EXP_VALUE/1e6:,.1f}M · ${YTD_EXP_PRICE:,.2f}/st average. Source: EIA-63C Table 8.</p>

  <h2>4 · EU benchmarks</h2>
  <div class="cards">
    <div class="card"><h3>DEPV — Germany, {esc(DEPV_LATEST)}</h3>
      <p>National: <b style="color:var(--amber)">6t €{DEPV6_L:,.2f}/t</b>
      ({delta_html(pct(DEPV6_L, DEPV6_P))} MoM) ·
      <b style="color:var(--amber)">26t €{DEPV26_L:,.2f}/t</b>
      ({delta_html(pct(DEPV26_L, DEPV26_P))} MoM). Regional split
      (Süd / Mitte / Nord-Ost by delivered quantity) in the
      <a href="sample-eubench.html">EU benchmarks sample</a>.</p></div>
    <div class="card"><h3>Baltpool — Lithuanian wood-chip SPOT</h3>
      <p>Sample weekly observation {esc(bp_last.period)}:
      <b style="color:var(--amber)">€{bp_last.value:,.2f}/MWh</b>
      ({delta_html(BP_WOW)} WoW). Recent prints: {" · ".join(f"{r.period} €{r.value:,.2f}" for _, r in bp.tail(4).iterrows())}.</p></div>
  </div>

  <h2>5 · Export destinations — {EX_YEAR} (UN Comtrade HS 4401.31)</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Destination</th><th class="num">Volume (metric tonnes)</th><th class="num">Value</th>
      <th class="num">Customs unit value ($/t)</th></tr></thead>
    <tbody>
{dest_rows()}
    </tbody>
  </table></div>
  <p class="caption">Annual {EX_YEAR} trade data for HS 440131 only. Weight is metric tonnes; unit value is reported customs value divided by net weight, not a purchase quote. No monthly destination service or individual buyer identification is available.</p>

  <div class="btnrow">
    <a class="btn" href="../index.html#pricing">Check product availability</a>
    <a class="btn ghost" href="../index.html#pricing">Availability</a>
  </div>
</div></section>
"""

# ================================================================ SAMPLE MILLDB
def full_mill_rows(df) -> str:
    out = []
    for _, r in df.iterrows():
        st = ('<span class="pill ok">Operating</span>'
              if r.status == "Currently Operating"
              else '<span class="pill idle">Temporarily idle</span>')
        out.append(f"<tr><td class='strong'>{esc(r.company)}</td><td>{esc(r.state)}</td>"
                   f"<td>{esc(r.region)}</td><td>{st}</td>"
                   f"<td class='num'>{fi(r.annual_capacity_tpy)}</td></tr>")
    return "\n".join(out)


reg_summary_rows = "\n".join(
    f"<tr><td class='strong'>{esc(idx)}</td><td class='num'>{int(r.n)}</td>"
    f"<td class='num'>{fi(r.cap)}</td></tr>"
    for idx, r in region_tbl.iterrows())

idle_rows = "\n".join(
    f"<tr><td class='strong'>{esc(r.company)}</td><td>{esc(r.state)}</td>"
    f"<td><span class='pill idle'>Temporarily Not in Operation</span></td>"
    f"<td class='num'>{fi(r.annual_capacity_tpy)}</td></tr>"
    for _, r in idle.iterrows())

sample_milldb_body = f"""
<section class="hero" style="padding-bottom:8px"><div class="wrap">
  <div class="kicker">Sample · mill database extract</div>
  <h1 style="font-size:28px">US pellet mill database — sample</h1>
  <p class="sub" style="font-size:15px">Selected {len(top15)} of {N_MILLS} listed US mills by annual capacity, excluding Enviva from the promotional extract. {N_OPERATING} were reported operating in the snapshot. This is not a current status check. Fetched 2026-09-03 from EIA-63C Table 1.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">
  <h2>Selected mills by listed capacity</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Mill</th><th>State</th><th>Region</th><th>Status</th>
      <th class="num">Capacity (tons/yr)</th></tr></thead>
    <tbody>
{full_mill_rows(top15)}
    </tbody>
  </table></div>

  <h2>Mills reported idle in the snapshot</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Mill</th><th>State</th><th>Status</th><th class="num">Capacity (tons/yr)</th></tr></thead>
    <tbody>
{idle_rows}
    </tbody>
  </table></div>

  <h2>By region — all {N_MILLS} tracked mills</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Region</th><th class="num">Mills</th><th class="num">Listed capacity (tons/yr)</th></tr></thead>
    <tbody>
{reg_summary_rows}
      <tr><td class="strong">Total</td><td class="num">{N_MILLS}</td><td class="num">{fi(TOTAL_CAP)}</td></tr>
    </tbody>
  </table></div>

  <div class="note"><b>Fields in the full mill file:</b> region · state · company · operational
  status · annual capacity (tons/yr) · source table · fetch timestamp. Statuses reported exactly
  as EIA publishes them. Capacity figures are EIA-listed nameplate, not verified output.</div>

  <div class="btnrow">
    <a class="btn" href="../index.html#pricing">Check product availability</a>
    <a class="btn ghost" href="../index.html#pricing">Availability</a>
  </div>
</div></section>
"""

# ================================================================ SAMPLE EUBENCH
def depv_nat_rows(n=14) -> str:
    out = []
    months = sorted(depv_nat.period.unique())[-n:]
    for m in months:
        r6 = depv_nat[(depv_nat.period == m) & (depv_nat.series_or_country == "DEPV 6t")].value
        r26 = depv_nat[(depv_nat.period == m) & (depv_nat.series_or_country == "DEPV 26t")].value
        v6 = f"{r6.iloc[0]:,.2f}" if len(r6) else "—"
        v26 = f"{r26.iloc[0]:,.2f}" if len(r26) else "—"
        out.append(f"<tr><td class='strong'>{esc(m)}</td><td class='num'>{v6}</td>"
                   f"<td class='num'>{v26}</td></tr>")
    return "\n".join(out)


def depv_region_rows() -> str:
    out = []
    reg = depv[(depv.period == DEPV_LATEST) & (~depv.series_or_country.str.startswith("DEPV "))]
    for _, r in reg.iterrows():
        out.append(f"<tr><td class='strong'>{esc(r.series_or_country)}</td>"
                   f"<td class='num'>{r.value:,.2f}</td></tr>")
    return "\n".join(out)


def bp_full_rows(n=13) -> str:
    out = []
    tail = bp.tail(n).reset_index(drop=True)
    for i, r in tail.iterrows():
        if i == 0:
            d = '<span style="color:var(--dim)">—</span>'
        else:
            d = delta_html(pct(r.value, tail.value[i - 1]))
        out.append(f"<tr><td class='strong'>{esc(r.period)}</td>"
                   f"<td class='num'>{r.value:,.2f}</td><td class='num'>{d}</td></tr>")
    return "\n".join(out)


sample_eubench_body = f"""
<section class="hero" style="padding-bottom:8px"><div class="wrap">
  <div class="kicker">Sample · EU benchmark series</div>
  <h1 style="font-size:28px">German pellet prices and Lithuanian wood-chip context</h1>
  <p class="sub" style="font-size:15px">DEPV German delivered pellet contract prices and, separately, Lithuanian wood-chip SPOT prices. These are different products and price bases, not an export-parity comparison.
  {esc(AS_OF)}.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">
  <h2>DEPV pelletpreis — Germany national, €/metric tonne</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Month</th><th class="num">DEPV 6t</th><th class="num">DEPV 26t</th></tr></thead>
    <tbody>
{depv_nat_rows(14)}
    </tbody>
  </table></div>
  <p class="caption">Sample month {esc(DEPV_LATEST)}: 6t €{DEPV6_L:,.2f} · 26t €{DEPV26_L:,.2f}.
  Monthly series; regional detail below. Source: DEPV (Deutscher Energieholz- und
  Pellet-Verband).</p>

  <h2>DEPV regional detail — {esc(DEPV_LATEST)}, €/metric tonne</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Region / delivery size</th><th class="num">€/metric tonne</th></tr></thead>
    <tbody>
{depv_region_rows()}
    </tbody>
  </table></div>
  <p class="caption">Süd / Mitte / Nord-Ost = South / Central / North-East Germany, by delivered
  quantity (3, 6 and 26 tonnes): all loose, blown-in ENplus A1 pellets, delivered within 50 km, including incidental costs and excluding VAT.</p>

  <h2>Baltpool Lithuanian wood-chip SPOT — €/MWh, last {len(bp.tail(13))} weekly prints</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Week</th><th class="num">€/MWh</th><th class="num">WoW</th></tr></thead>
    <tbody>
{bp_full_rows(13)}
    </tbody>
  </table></div>
  <p class="caption">Series in the dataset runs {esc(bp.period.iloc[0])} → {esc(bp_last.period)}
  ({len(bp)} weekly prints). 12-month range: €{bp[bp.period >= '2025-09'].value.min():,.2f} –
  €{bp[bp.period >= '2025-09'].value.max():,.2f}/MWh. Source: BaltPool.</p>

  <div class="note"><b>Different products:</b> DEPV measures delivered ENplus A1 pellet prices in Germany, excluding VAT. Baltpool type=spot, country=lt is Lithuanian wood-chip SPOT. Its separate wood-pellet index uses type=wood_pellets_spot and is not displayed here. No currency, energy, grade or freight normalization has been applied.</div>

  <div class="btnrow">
    <a class="btn" href="../index.html#pricing">Check product availability</a>
    <a class="btn ghost" href="../index.html#pricing">Availability</a>
  </div>
</div></section>
"""

page("Sample digest — Pellet Market Monitor", sample_digest_body, sample=True) \
    if False else None  # written below via write()
(SAMPLE / "sample-digest.html").write_text(
    page("Sample digest — Pellet Market Monitor", sample_digest_body, sample=True),
    encoding="utf-8")
(SAMPLE / "sample-milldb.html").write_text(
    page("Sample mill database — Pellet Market Monitor", sample_milldb_body, sample=True),
    encoding="utf-8")
(SAMPLE / "sample-eubench.html").write_text(
    page("Sample EU benchmarks — Pellet Market Monitor", sample_eubench_body, sample=True),
    encoding="utf-8")
(HERE / "index.html").write_text(index_html, encoding="utf-8")

# ================================================================ DATARADE LISTING
dest_line = " · ".join(f"{r.destination_country} {fi(r.quantity_tons)} t" for _, r in TOP_DEST.iterrows())
datarade = f"""# Pellet Market Monitor — corrected product draft

Status: research prototype. Paid orders, weekly subscriber delivery and automated alerts are unavailable. This file does not update an external marketplace listing.

Free dated sample: US production, feedstock costs and export averages (EIA May 2026); German delivered ENplus A1 pellet contract prices excluding VAT (DEPV August 2026); separate Lithuanian wood-chip SPOT context (Baltpool type=spot, country=lt); annual US pellet exports by destination (Comtrade 2024, HS 440131).

The sample preserves inputs fetched September 3, 2026. Descriptions corrected September 20, 2026. No claim of current prices, price parity, verified buyers, ten-year history or delivered subscriber alerts is made.

ENplus contains producers, not established buyers. Comtrade unit values are historical customs value/net weight, not purchase quotes. Tables retain their original units and periods.

Previous proposed prices ($49/month, $499/year, $99 dataset pack) are paused, not available offers. Validate sources, coverage and delivery before publishing any paid listing.

Contact: {EMAIL}
"""

(HERE / "datarade-listing.md").write_text(datarade, encoding="utf-8")

print("written:")
for p in [HERE / "index.html", SAMPLE / "sample-digest.html",
          SAMPLE / "sample-milldb.html", SAMPLE / "sample-eubench.html",
          HERE / "datarade-listing.md"]:
    print(" ", p, p.stat().st_size, "bytes")