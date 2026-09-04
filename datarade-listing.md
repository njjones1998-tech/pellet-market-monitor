# Datarade listing — Pellet Market Monitor

Paste-ready text for https://datarade.ai/company/contact/data-providers.
Keep the monitoring/alerts angle per charter §0.5; no exclusivity claims per §0.6.
Numbers below are a snapshot as of 2026-09-03 — refresh before submitting if >2 weeks old.

---

## Product name

**Pellet Market Monitor** — constant US + EU wood-pellet price monitoring with alerts

## Provider

Scriptores Helm LLC (Mississippi, USA) · contact: njjones1999@gmail.com

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

- US mills: 87 mills tracked (85 operating), 13,098,872 tons/yr listed
  capacity across East/South/West regions — each with state, region, operational status,
  capacity (EIA-63C Table 1).
- US production (latest EIA month, May 2026): 931,315 short tons total
  (127,679 premium/standard + 803,636 utility); YTD 4,435,579 short tons.
- Feedstock costs (May 2026): roundwood/pulpwood $26.02/ton,
  sawmill residuals $34.79/ton (EIA-63C Table 3; withheld values
  reported as withheld, never imputed).
- Exports (May 2026): 808,518 short tons at $205.71/short ton
  average (EIA-63C Table 8).
- EU benchmarks: DEPV 2026-08 — 6t €399.74/ton, 26t €383.40/ton (plus
  regional Süd/Mitte/Nord-Ost detail); BaltPool weekly spot — latest print 2026-09-01
  €29.46/MWh.
- Export destinations (2024, UN Comtrade HS 4401.31): United Kingdom 7,004,305 t · Japan 1,150,033 t · Netherlands 659,378 t · Denmark 648,648 t;
  world total 10,004,015 tons / $1,859M.
- Buyer map: 38 destination countries matched against the
  ENplus producer directory (2,212 producers, 1,420 active across 60 countries).

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
