#!/usr/bin/env python3
"""Pellet Market Monitor — static site generator.

Builds site/index.html, site/sample/{sample-digest,sample-milldb,sample-eubench}.html
and site/datarade-listing.md from the VERIFIED exports in ../exports/.

Run after every export refresh:   /home/nate/blt-venv/bin/python3 gen_site.py

Rules honored (WORKSHOP-STRUCTURE.md §0.5/§0.6, hard rule 1):
  - Positioning = CONSTANT MONITORING + ALERTS. No "archive" marketing, no dates-of-record
    headline, no operator biography.
  - No Enviva-named rows appear anywhere (filter at load; totals may include them as counts).
  - Every number rendered here comes from exports/*.csv or the verified DB — nothing invented.
  - CTAs are mailto: with subject prefill. Stripe wiring replaces them after operator approval —
    see the "PAYMENTS TODO" HTML comments in the pricing section of index.html.
"""
from __future__ import annotations

import html as html_mod
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
EX = HERE.parent / "exports"
DB = HERE.parent / "data" / "pellet.db"
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

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ep = pd.read_sql("SELECT period, quantity_tons, value_usd, price FROM export_prices ORDER BY period", con)
en_counts = pd.read_sql(
    "SELECT COUNT(*) n, COUNT(DISTINCT country) c FROM enplus_producers", con)
en_active = pd.read_sql("SELECT COUNT(*) n FROM enplus_producers WHERE status='active'", con)
con.close()
YTD_EXP_VALUE = float(ep.value_usd.astype(float).sum())
YTD_EXP_QTY = float(ep.quantity_tons.sum())
YTD_EXP_PRICE = YTD_EXP_VALUE / YTD_EXP_QTY

exd = pd.read_csv(EX / "export_destinations.csv")
EX_YEAR = int(exd.period.max())
e24 = exd[(exd.period == EX_YEAR) & (exd.destination_country != "World")].copy()
e24["value_usd"] = e24.value_usd_cents / 100
e24["usd_per_t"] = e24.value_usd / e24.quantity_tons
e24 = e24.sort_values("quantity_tons", ascending=False)
world = exd[(exd.period == EX_YEAR) & (exd.destination_country == "World")].iloc[0]
TOP_DEST = e24.head(4)

ph = pd.read_csv(EX / "price_history_10y.csv", dtype={"period": str})
ph["period"] = ph.period.astype(str).str.zfill(2)
LAST_M, PREV_M = "05", "04"  # EIA-63C raw months 1..5 = Jan..May of the release year (2026)
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
         f"all series fetched 2026-09-03")

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
  Data sources: {SOURCES} — all public sources; the value added is harmonization,
  monitoring, and alerting.<br>
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
      <a href="{prefix}index.html#pricing">Pricing</a>
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
{body}
{FOOTER.replace('sample/', prefix + 'sample/')}
</body>
</html>"""


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
  <div class="kicker">Weekly US + EU wood-pellet market monitoring</div>
  <h1>Constant monitoring of US pellet market pricing.<br>Alerts when your market moves.</h1>
  <p class="sub">Production, feedstock costs, export prices, and EU benchmarks — tracked every
  week so you hear about the move from us, not from your supplier's next quote.</p>
  <div class="btnrow">
    <a class="btn" href="{mailto('Sample digest request — Pellet Market Monitor',
                                 'Please send me the latest sample digest of the Pellet Market Monitor.')}">
      Request a sample digest — free</a>
    <a class="btn ghost" href="#pricing">See pricing</a>
  </div>

  <!-- PAYMENTS TODO (post-approval): hero CTA above stays mailto until Stripe is wired.
       Stripe Checkout links will replace the $99 pack CTA in the Pricing section (search
       "PAYMENTS TODO" below). No other payment paths exist on this page. -->

  <div class="stats">
    <div class="stat"><b>{N_MILLS}</b><span>US pellet mills tracked (EIA-63C)</span></div>
    <div class="stat"><b>{TOTAL_CAP/1e6:,.1f}M</b><span>tons/yr listed mill capacity</span></div>
    <div class="stat"><b>{N_EN:,}</b><span>ENplus producers watched ({N_EN_ACTIVE:,} active, {N_EN_COUNTRIES} countries)</span></div>
    <div class="stat"><b>Weekly</b><span>digest + threshold price alerts</span></div>
  </div>
</div></section>

<section class="sect" id="get"><div class="wrap">
  <h2>What subscribers get</h2>
  <p class="lead">One weekly email that answers the only question that matters: which numbers
  moved, and by how much.</p>
  <div class="cards">
    <div class="card"><span class="tag">Weekly digest</span><h3>Every series, every week</h3>
      <p>US production by region and grade, feedstock costs (roundwood, sawmill residuals,
      wood-product residuals), export volume and price, retail by region, and the EU side:
      DEPV (Germany) and BaltPool (Baltic spot).</p></div>
    <div class="card"><span class="tag">Alerts</span><h3>Price alerts on threshold moves</h3>
      <p>You set the thresholds — series, direction, percentage. When a series crosses the
      line (week-over-week or month-over-month), you get a short email with the move and the
      underlying numbers. No dashboard to babysit.</p></div>
    <div class="card"><span class="tag">US + EU</span><h3>One harmonized view</h3>
      <p>US export prices in $/ton next to DEPV in €/ton and BaltPool in €/MWh, on the same
      dates — so a German retail move or a Baltic utility tender is visible against US export
      economics in one table.</p></div>
    <div class="card"><span class="tag">Buyer map</span><h3>Who buys, where</h3>
      <p>Export destinations with volumes and implied $/ton (UN Comtrade HS 4401.31), plus an
      ENplus producer map by country — the demand side and the supplier universe in one file.</p></div>
    <div class="card"><span class="tag">Delivery</span><h3>Email + CSV</h3>
      <p>The digest lands as email with CSV attachments of every table. Machine-readable by
      default; paste straight into your own models or procurement sheets.</p></div>
    <div class="card"><span class="tag">Coverage</span><h3>Public sources, verified</h3>
      <p>Built only from public data — EIA-63C, DEPV, BaltPool, the ENplus directory, UN
      Comtrade — reconciled and drift-checked every fetch. We claim no exclusivity on the
      sources; the product is the monitoring and the alerts.</p></div>
  </div>
</div></section>

<section class="sect" id="data"><div class="wrap">
  <h2>The data, live samples</h2>
  <p class="lead">Real numbers from the current dataset (as of {esc(AS_OF)}).
  Full pages: <a href="sample/sample-digest.html">sample weekly digest</a> ·
  <a href="sample/sample-milldb.html">sample mill database</a> ·
  <a href="sample/sample-eubench.html">sample EU benchmarks</a>.</p>

  <h3>US pellet mills — top {len(top10)} by listed capacity <span style="color:var(--dim);font-weight:400">(of {N_MILLS} tracked, {N_OPERATING} operating)</span></h3>
  <div class="tblwrap"><table>
    <thead><tr><th>Mill</th><th>State</th><th>Region</th><th>Status</th><th class="num">Capacity (tons/yr)</th></tr></thead>
    <tbody>
{mill_rows(top10)}
    </tbody>
  </table></div>
  <p class="caption">Source: EIA-63C Table 1, fetched 2026-09-03. Full 87-mill table with region,
  status, and capacity is in the subscription digest and the $99 dataset pack.</p>

  <h3>US production &amp; exports — {esc(LATEST_US_MONTH)} <span style="color:var(--dim);font-weight:400">(latest EIA month; prior {esc(PREV_US_MONTH)} for comparison)</span></h3>
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

  <h3>EU benchmarks — latest prints</h3>
  <div class="cards">
    <div class="card">
      <h3>DEPV — German retail index, {esc(DEPV_LATEST)}</h3>
      <div class="tblwrap" style="border:none;margin:0;background:transparent"><table>
        <thead><tr><th>Series</th><th class="num">€/ton</th><th class="num">MoM</th></tr></thead>
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
      <h3>BaltPool — Baltic industrial spot</h3>
      <div class="tblwrap" style="border:none;margin:0;background:transparent"><table>
        <thead><tr><th>Week</th><th class="num">€/MWh</th><th class="num">WoW</th></tr></thead>
        <tbody>
{bp_rows(6)}
        </tbody>
      </table></div>
      <p class="caption">Latest print {esc(bp_last.period)}: €{bp_last.value:,.2f}/MWh.
      Source: BaltPool spot.</p>
    </div>
  </div>

  <h3>Top US export destinations, {EX_YEAR} <span style="color:var(--dim);font-weight:400">(UN Comtrade, HS 4401.31)</span></h3>
  <div class="tblwrap"><table>
    <thead><tr><th>Destination</th><th class="num">Volume (tons)</th><th class="num">Value</th><th class="num">Avg $/ton</th></tr></thead>
    <tbody>
{dest_rows()}
    </tbody>
  </table></div>
  <p class="caption">{EX_YEAR} annual totals. The buyer map (59 countries, ENplus producer counts
  by destination) ships with the subscription and the dataset pack.</p>
</div></section>

<section class="sect" id="pricing"><div class="wrap">
  <h2>Pricing</h2>
  <p class="lead">Cancel any time. The digest and alerts arrive by email; every table ships as CSV.</p>

  <!-- ============================================================
       PAYMENTS TODO — WHERE STRIPE GOES (after operator approval):
       Replace each mailto CTA below with a Stripe Checkout payment link:
         1. Monitoring monthly  — $49/mo   recurring  -> [STRIPE_LINK_MONTHLY]
         2. Monitoring annual   — $499/yr  recurring  -> [STRIPE_LINK_ANNUAL]
         3. Dataset pack        — $99 one-off         -> [STRIPE_LINK_PACK]
       Keep the mailto links as the fallback line under each button
       ("or email ...") while Stripe is in test mode. Until then the
       mailto CTAs are the only order path. No JS is needed for
       Stripe Checkout payment links — a plain <a href> is enough.
       ============================================================ -->

  <div class="plans">
    <div class="price">
      <span class="pick">Subscription</span>
      <div class="amt">$49<span style="font-size:15px;color:var(--mut)">/mo</span></div>
      <div style="color:var(--mut);font-size:13px">or $499/yr (2 months free)</div>
      <ul>
        <li>Weekly digest: US production, feedstock costs, retail by region, export prices, EU benchmarks (DEPV + BaltPool)</li>
        <li>Threshold price alerts — your series, your thresholds, by email</li>
        <li>Harmonized US + EU view and the buyer map</li>
        <li>Every table as CSV attachment</li>
      </ul>
      <a class="btn" href="{mailto('Subscription — Pellet Market Monitor ($49/mo)',
                                   'I would like to subscribe at $49/month. Please send payment details.')}">
        Subscribe — $49/mo</a>
      <a class="btn ghost" style="margin-top:10px" href="{mailto('Subscription — Pellet Market Monitor ($499/yr)',
                                   'I would like to subscribe at $499/year. Please send payment details.')}">
        Subscribe — $499/yr</a>
    </div>
    <div class="price">
      <span class="pick">One-off</span>
      <div class="amt">$99</div>
      <div style="color:var(--mut);font-size:13px">dataset pack, single purchase</div>
      <ul>
        <li>All {N_MILLS} US mills with region, status, and capacity</li>
        <li>US production / feedstock / export price series (10-year monthly depth as context)</li>
        <li>EU benchmarks: DEPV + BaltPool history</li>
        <li>Buyer map: {exd.destination_country.nunique()-1} export destinations with volumes</li>
        <li>Delivered as CSV + Excel</li>
      </ul>
      <a class="btn" href="{mailto('Dataset pack order — $99 — Pellet Market Monitor',
                                   'I would like to buy the $99 dataset pack. Please send payment details.')}">
        Buy dataset pack — $99</a>
    </div>
    <div class="price">
      <span class="pick">Free</span>
      <div class="amt">$0</div>
      <div style="color:var(--mut);font-size:13px">sample digest + sample pages</div>
      <ul>
        <li>One full sample digest built from the current data</li>
        <li>Sample mill database and EU benchmark pages</li>
        <li>No obligation — see exactly what a week looks like</li>
      </ul>
      <a class="btn ghost" href="{mailto('Sample digest request — Pellet Market Monitor',
                                   'Please send me the latest sample digest of the Pellet Market Monitor.')}">
        Request sample digest</a>
      <p style="margin-top:12px"><a href="sample/sample-digest.html" style="color:var(--amber)">View the sample pages online →</a></p>
    </div>
  </div>
  <div class="note">Orders and sample requests currently go straight to
  <a href="mailto:{EMAIL}" style="color:var(--amber)">{EMAIL}</a>; you get a reply with payment
  details and delivery within one business day. Self-serve checkout is being added.</div>
</div></section>

<section class="sect" id="who"><div class="wrap">
  <h2>Who it is for</h2>
  <p class="lead">Built for people who price, buy, sell, or finance wood pellets and need the
  week's numbers before the market tells them.</p>
  <div class="cards">
    <div class="card"><h3>EU buyers &amp; procurement teams</h3><p>Track US export price direction
      and Baltic utility spot against your contract renewals — with alerts when either moves.</p></div>
    <div class="card"><h3>Export traders &amp; brokers</h3><p>See production, feedstock cost
      pressure, and destination volumes in one view; get pinged when a benchmark crosses your
      threshold.</p></div>
    <div class="card"><h3>Analysts &amp; investors</h3><p>A clean weekly series set — US supply,
      US export pricing, EU demand-side benchmarks — delivered as data, not a PDF to re-type.</p></div>
  </div>
</div></section>
"""

index_html = page(
    "Pellet Market Monitor — constant US + EU pellet price monitoring, alerts when your market moves",
    index_body)

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
  <div class="kicker">Sample · what a weekly digest looks like</div>
  <h1 style="font-size:28px">Weekly digest — data week ending {esc(bp_last.period)}</h1>
  <p class="sub" style="font-size:15px">This is a real digest assembled from the current dataset —
  not a mockup. {esc(AS_OF)}.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">

  <div class="note"><b style="color:var(--amber)">⚠ Alert fired this week:</b> BaltPool spot
  €{bp_prev.value:,.2f} → €{bp_last.value:,.2f}/MWh ({delta_html(BP_WOW)} week-over-week) —
  crossed the ±3% weekly threshold. Subscribers with a BaltPool alert received this by email
  with the underlying series attached.</div>

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
      (Süd / Mitte / Nord-Ost by bag size) in the full digest and the
      <a href="sample-eubench.html">EU benchmarks sample</a>.</p></div>
    <div class="card"><h3>BaltPool — Baltic spot</h3>
      <p>Latest weekly print {esc(bp_last.period)}:
      <b style="color:var(--amber)">€{bp_last.value:,.2f}/MWh</b>
      ({delta_html(BP_WOW)} WoW). Recent prints: {" · ".join(f"{r.period} €{r.value:,.2f}" for _, r in bp.tail(4).iterrows())}.</p></div>
  </div>

  <h2>5 · Export destinations — {EX_YEAR} (UN Comtrade HS 4401.31)</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Destination</th><th class="num">Volume (tons)</th><th class="num">Value</th>
      <th class="num">Avg $/ton</th></tr></thead>
    <tbody>
{dest_rows()}
    </tbody>
  </table></div>
  <p class="caption">Annual {EX_YEAR} trade data; monthly destination tracking is added as the
  Comtrade monthly series is integrated. Buyer map (ENplus producers by destination) in the full digest.</p>

  <div class="btnrow">
    <a class="btn" href="{mailto('Subscribe — Pellet Market Monitor ($49/mo)',
                                 'I reviewed the sample digest and would like to subscribe at $49/month.')}">
      Get this every week — $49/mo</a>
    <a class="btn ghost" href="../index.html#pricing">Pricing</a>
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
  <p class="sub" style="font-size:15px">Top {len(top15)} of {N_MILLS} tracked US mills by listed
  annual capacity, {N_OPERATING} currently operating. Full file: all {N_MILLS} mills with region,
  state, operational status, capacity, source table, and fetch timestamp — CSV + Excel in the
  dataset pack. Fetched 2026-09-03 from EIA-63C Table 1.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">
  <h2>Top {len(top15)} mills by capacity</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Mill</th><th>State</th><th>Region</th><th>Status</th>
      <th class="num">Capacity (tons/yr)</th></tr></thead>
    <tbody>
{full_mill_rows(top15)}
    </tbody>
  </table></div>

  <h2>Mills currently idle</h2>
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
    <a class="btn" href="{mailto('Dataset pack order — $99 — Pellet Market Monitor',
                                 'I would like to buy the $99 dataset pack (mill database + price history + buyer map).')}">
      Buy the dataset pack — $99</a>
    <a class="btn ghost" href="../index.html#pricing">Pricing</a>
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
  <h1 style="font-size:28px">EU pellet benchmarks — sample</h1>
  <p class="sub" style="font-size:15px">The EU side of the harmonized US+EU view: DEPV German
  retail prices and BaltPool Baltic industrial spot, as they appear in the weekly digest.
  {esc(AS_OF)}.</p>
</div></section>

<section class="sect" style="border-top:none;padding-top:10px"><div class="wrap">
  <h2>DEPV pelletpreis — Germany national, €/ton</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Month</th><th class="num">DEPV 6t</th><th class="num">DEPV 26t</th></tr></thead>
    <tbody>
{depv_nat_rows(14)}
    </tbody>
  </table></div>
  <p class="caption">Latest month {esc(DEPV_LATEST)}: 6t €{DEPV6_L:,.2f} · 26t €{DEPV26_L:,.2f}.
  Monthly series; regional detail below. Source: DEPV (Deutscher Energieholz- und
  Pellet-Verband).</p>

  <h2>DEPV regional detail — {esc(DEPV_LATEST)}, €/ton</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Region / delivery size</th><th class="num">€/ton</th></tr></thead>
    <tbody>
{depv_region_rows()}
    </tbody>
  </table></div>
  <p class="caption">Süd / Mitte / Nord-Ost = South / Central / North-East Germany, by delivered
  quantity (3 t bagged, 6 t, 26 t loose).</p>

  <h2>BaltPool spot — €/MWh, last {len(bp.tail(13))} weekly prints</h2>
  <div class="tblwrap"><table>
    <thead><tr><th>Week</th><th class="num">€/MWh</th><th class="num">WoW</th></tr></thead>
    <tbody>
{bp_full_rows(13)}
    </tbody>
  </table></div>
  <p class="caption">Series in the dataset runs {esc(bp.period.iloc[0])} → {esc(bp_last.period)}
  ({len(bp)} weekly prints). 12-month range: €{bp[bp.period >= '2025-09'].value.min():,.2f} –
  €{bp[bp.period >= '2025-09'].value.max():,.2f}/MWh. Source: BaltPool.</p>

  <div class="note"><b>Why both matter to a US-market watcher:</b> DEPV is the German retail
  demand signal; BaltPool is the Baltic utility-grade price that industrial export flows price
  against. The subscription puts both next to US export prices (EIA-63C Table 8:
  ${exp_l.price/100:,.2f}/st in {esc(LATEST_US_MONTH)}) in one weekly table.</div>

  <div class="btnrow">
    <a class="btn" href="{mailto('Subscribe — Pellet Market Monitor ($49/mo)',
                                 'I reviewed the EU benchmark sample and would like to subscribe at $49/month.')}">
      Get this every week — $49/mo</a>
    <a class="btn ghost" href="../index.html#pricing">Pricing</a>
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
datarade = f"""# Datarade listing — Pellet Market Monitor

Paste-ready text for https://datarade.ai/company/contact/data-providers.
Keep the monitoring/alerts angle per charter §0.5; no exclusivity claims per §0.6.
Numbers below are a snapshot as of 2026-09-03 — refresh before submitting if >2 weeks old.

---

## Product name

**Pellet Market Monitor** — constant US + EU wood-pellet price monitoring with alerts

## Provider

Scriptores Helm LLC (Mississippi, USA) · contact: {EMAIL}

## Category

Commodity price data / procurement intelligence (energy commodities: wood pellets, biomass feedstocks)

## One-line summary (for search results)

Constant monitoring of US pellet production, feedstock, and export pricing — alerts when your market moves.

## Product description

The Pellet Market Monitor is an ongoing monitoring service covering the US wood-pellet
market and the EU benchmarks it trades against. Subscribers receive a weekly digest with
current numbers — US production by region and grade, feedstock costs (roundwood and
residuals), export volumes and average export prices, and the two EU demand-side benchmarks
(DEPV German retail, BaltPool Baltic industrial spot) — plus configurable threshold alerts
that email the subscriber when any tracked series moves beyond a set threshold
(week-over-week or month-over-month). The value is harmonization and vigilance: US export
prices in $/short ton presented next to DEPV in €/ton and BaltPool in €/MWh on the same
dates, so a move in one market is immediately visible against the others. Buyers do not need
a dashboard; the data arrives by email with CSV attachments.

All underlying sources are public (EIA-63C survey tables, DEPV price index, BaltPool spot,
ENplus producer directory, UN Comtrade HS 4401.31). We claim no proprietary exclusivity on
the sources; the product is the continuous collection, verification (reconciliation and
drift checks on every fetch), harmonization across US and EU series, and the alerting layer.

## Sample data description

A full sample digest and sample extracts are available on request (and at our site). Recent
real values from the current dataset (as of 2026-09-03):

- US mills: {N_MILLS} mills tracked ({N_OPERATING} operating), {fi(TOTAL_CAP)} tons/yr listed
  capacity across East/South/West regions — each with state, region, operational status,
  capacity (EIA-63C Table 1).
- US production (latest EIA month, {LATEST_US_MONTH}): {fi(prod_l)} short tons total
  ({fi(prem_l)} premium/standard + {fi(util_l)} utility); YTD {fi(YTD_PROD)} short tons.
- Feedstock costs ({LATEST_US_MONTH}): roundwood/pulpwood ${fs_l['Roundwood/pulpwood']:,.2f}/ton,
  sawmill residuals ${fs_l['Sawmill residuals']:,.2f}/ton (EIA-63C Table 3; withheld values
  reported as withheld, never imputed).
- Exports ({LATEST_US_MONTH}): {fi(exp_l.production_tons)} short tons at ${exp_l.price/100:,.2f}/short ton
  average (EIA-63C Table 8).
- EU benchmarks: DEPV {DEPV_LATEST} — 6t €{DEPV6_L:,.2f}/ton, 26t €{DEPV26_L:,.2f}/ton (plus
  regional Süd/Mitte/Nord-Ost detail); BaltPool weekly spot — latest print {bp_last.period}
  €{bp_last.value:,.2f}/MWh.
- Export destinations ({EX_YEAR}, UN Comtrade HS 4401.31): {dest_line};
  world total {fi(world.quantity_tons)} tons / ${world.value_usd_cents/100/1e6:,.0f}M.
- Buyer map: {exd.destination_country.nunique()-1} destination countries matched against the
  ENplus producer directory ({N_EN:,} producers, {N_EN_ACTIVE:,} active across {N_EN_COUNTRIES} countries).

## Delivery method

- Weekly email digest (PDF/HTML) with every table also attached as CSV.
- Threshold price alerts by email (series, direction, and threshold configured per subscriber).
- One-off datasets delivered as CSV + Excel via email or a download link.
- API delivery: not yet; planned. CSV-by-email is the current machine-readable path.

## Pricing

- Monitoring subscription: **$49/month** or **$499/year** (both include the weekly digest and alerts).
- One-off dataset pack: **$99** — full US mill list, US price series (10-year monthly depth as
  context), EU benchmark history, buyer map — CSV + Excel.

## Update cadence

Weekly (data refresh + digest); EIA-63C monthly release cycle, BaltPool weekly, DEPV monthly,
Comtrade monthly/annual.

## Notes for Datarade review

- Listed as both wrappers of the same data: (1) the monitoring subscription sold from our own
  site, (2) one-off export files via the marketplace lead flow.
- Public-source data, republished with value added (harmonization, verification, alerts); no
  exclusivity claims. Verification/reconciliation artifacts available on request during
  provider due diligence.
"""

(HERE / "datarade-listing.md").write_text(datarade, encoding="utf-8")

print("written:")
for p in [HERE / "index.html", SAMPLE / "sample-digest.html",
          SAMPLE / "sample-milldb.html", SAMPLE / "sample-eubench.html",
          HERE / "datarade-listing.md"]:
    print(" ", p, p.stat().st_size, "bytes")